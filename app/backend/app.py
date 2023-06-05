import os
import mimetypes
import time
import logging
import openai
import json
from flask import Flask, request, jsonify
from flask_restx import Resource, Api, fields 

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from approaches.retrievethenread import RetrieveThenReadApproach
from approaches.readretrieveread import ReadRetrieveReadApproach
from approaches.readdecomposeask import ReadDecomposeAsk
from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach
from azure.storage.blob import BlobServiceClient

# Replace these with your own values, either in environment variables or directly here
AZURE_BLOB_STORAGE_ACCOUNT = os.environ.get("AZURE_BLOB_STORAGE_ACCOUNT") or "mystorageaccount"
AZURE_BLOB_STORAGE_CONTAINER = os.environ.get("AZURE_BLOB_STORAGE_CONTAINER") or "content"
AZURE_SEARCH_SERVICE = os.environ.get("AZURE_SEARCH_SERVICE") or "gptkb"
AZURE_SEARCH_INDEX = os.environ.get("AZURE_SEARCH_INDEX") or "bushoindex"
AZURE_OPENAI_SERVICE = os.environ.get("AZURE_OPENAI_SERVICE") or "myopenai"
AZURE_OPENAI_GPT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_GPT_DEPLOYMENT") or "davinci"
AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHATGPT_DEPLOYMENT") or "chat"

KB_FIELDS_CONTENT = os.environ.get("KB_FIELDS_CONTENT") or "content"
KB_FIELDS_CATEGORY = os.environ.get("KB_FIELDS_CATEGORY") or "category"
KB_FIELDS_SOURCEPAGE = os.environ.get("KB_FIELDS_SOURCEPAGE") or "sourcepage"

# Use the current user identity to authenticate with Azure OpenAI, Cognitive Search and Blob Storage (no secrets needed, 
# just use 'az login' locally, and managed identity when deployed on Azure). If you need to use keys, use separate AzureKeyCredential instances with the 
# keys for each service
# If you encounter a blocking error during a DefaultAzureCredntial resolution, you can exclude the problematic credential by using a parameter (ex. exclude_shared_token_cache_credential=True)
azure_credential = DefaultAzureCredential(exclude_shared_token_cache_credential=True)


# Used by the OpenAI SDK
openai.api_type = "azure"
openai.api_base = f"https://{AZURE_OPENAI_SERVICE}.openai.azure.com"
openai.api_version = "2022-12-01"

# Comment these two lines out if using keys, set your API key in the OPENAI_API_KEY environment variable instead
openai.api_type = "azure_ad"
openai_token = azure_credential.get_token("https://cognitiveservices.azure.com/.default")
openai.api_key = openai_token.token

# Set up clients for Cognitive Search and Storage
search_client = SearchClient(
    endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
    index_name=AZURE_SEARCH_INDEX,
    credential=azure_credential)
blob_client = BlobServiceClient(
    account_url=f"https://{AZURE_BLOB_STORAGE_ACCOUNT}.blob.core.windows.net", 
    credential=azure_credential)
blob_container = blob_client.get_container_client(AZURE_BLOB_STORAGE_CONTAINER)

# Various approaches to integrate GPT and external knowledge, most applications will use a single one of these patterns
# or some derivative, here we include several for exploration purposes
ask_approaches = {
    "rtr": RetrieveThenReadApproach(search_client, AZURE_OPENAI_GPT_DEPLOYMENT, KB_FIELDS_SOURCEPAGE, KB_FIELDS_CONTENT),
    "rrr": ReadRetrieveReadApproach(search_client, AZURE_OPENAI_GPT_DEPLOYMENT, KB_FIELDS_SOURCEPAGE, KB_FIELDS_CONTENT),
    "rda": ReadDecomposeAsk(search_client, AZURE_OPENAI_GPT_DEPLOYMENT, KB_FIELDS_SOURCEPAGE, KB_FIELDS_CONTENT)
}

chat_approaches = {
    "rrr": ChatReadRetrieveReadApproach(search_client, AZURE_OPENAI_CHATGPT_DEPLOYMENT, AZURE_OPENAI_GPT_DEPLOYMENT, KB_FIELDS_SOURCEPAGE, KB_FIELDS_CONTENT)
}

app = Flask(__name__)
app.config.SWAGGER_UI_DOC_EXPANSION = 'list'
app.config['JSON_AS_ASCII'] = False

api = Api(app, 
        version='0.0.1', 
        title='Enterprise search API using Azure OpenAI Service', 
        description='Azure OpenAI ServiceとAzure Cognitive Searchをつかった業務データの検索APIです',
        doc='/docs/') 

# モデルの定義
ask_model = api.model('ask', {
    'approach': fields.String(required=True, description='rtr(Retrive-Then-Read) or rrr(ead-Retrive-Read) or rda(Read-Decompose-Ask)'),
    'question': fields.String(required=True, description='some questions to ask')
})

chat_model = api.model('response', {
    'history': fields.List(fields.Nested(api.model('response_history', {
        'user': fields.String(required=True, description='user message history'),
        'bot': fields.String(description='chatbot message history')
    })), description='user and bot message history', required=True),
    'overrides': fields.Nested(api.model('response_overrides', {
        'semantic_ranker': fields.Boolean(description='use semantic ranker'),
        'semantic_captions': fields.Boolean(description='use semantic captions'),
        'top': fields.Integer(description='number of responses to retrieve'),
        'suggest_followup_questions': fields.Boolean(description='suggest followup questions')
    }))
})

answer_model = api.model('answer', {
    'answer': fields.String,
    'data_points': fields.List(fields.String()),
    'thoughts': fields.String
})

error_model = api.model('error', {
    'error': fields.String
})

# /ask エンドポイント-- リクエストを送ると、レスポンスで回答が返る
@api.route("/ask", endpoint='ask')
@api.header('content-type', 'application/json')
class Ask(Resource):
    @api.doc(body=ask_model)
    @api.response(200, 'Success', answer_model)
    @api.response(400, 'Bad Request', error_model)
    @api.response(500, 'Internal Server Error', error_model)
    def post(answer_model):
        ensure_openai_token()
        approach = request.json["approach"]
        try:
            impl = ask_approaches.get(approach)
            if not impl:
                return jsonify({"error": "unknown approach"}), 400
            r = impl.run(request.json["question"], request.json.get("overrides") or {}) 
            return jsonify(r)
        except Exception as e:
            logging.exception("Exception in /ask")
            return jsonify({"error": str(e)}), 500

# /chat エンドポイント-- リクエストを送ると、過去履歴をもとにチャットで対話ができる
@api.route("/chat", endpoint='chat')
@api.header('content-type', 'application/json')
class Chat(Resource):
    @api.doc(body=chat_model)
    @api.response(200, 'Success', answer_model)
    @api.response(400, 'Bad Request', error_model)
    @api.response(500, 'Internal Server Error', error_model)
    def post(answer_model):
        ensure_openai_token()
        approach = request.json["approach"]
        try:
            impl = chat_approaches.get(approach)
            if not impl:
                return jsonify({"error": "unknown approach"}), 400
            r = impl.run(request.json["history"], request.json.get("overrides") or {})
            return jsonify(r)
        except Exception as e:
            logging.exception("Exception in /chat")
            return jsonify({"error": str(e)}), 500


# Serve content files from blob storage from within the app to keep the example self-contained. 
# *** NOTE *** this assumes that the content files are public, or at least that all users of the app
# can access all the files. This is also slow and memory hungry.
@api.route("/content/<string:path>")
class Content(Resource):
    def get(self, path):
        print(path)
        blob = blob_container.get_blob_client(path).download_blob()
        mime_type = blob.properties["content_settings"]["content_type"]
        if mime_type == "application/octet-stream":
            mime_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
        return blob.readall(), 200, {"Content-Type": mime_type, "Content-Disposition": f"inline; filename={path}"}


def ensure_openai_token():
    global openai_token
    if openai_token.expires_on < int(time.time()) - 60:
        openai_token = azure_credential.get_token("https://cognitiveservices.azure.com/.default")
        openai.api_key = openai_token.token
    
if __name__ == "__main__":
    app.run()
