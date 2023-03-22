#!/usr/bin/env python3
import os
import re
import json
import socket
import requests
from pathlib import Path
import aspose.words as aw
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file


# ============== CONFIG =====================

# IP of flask app host:
# 127.0.0.1 will only allow local access from your current machine
# 0.0.0.0 will allow remote access from local network
FLASK_HOST = "0.0.0.0"

# Port of flask app:
# Change it to anything you like (should be larger than 1024)
FLASK_PORT = 47118

# Replace your HTTP proxy host and port here
# The OpenAI API requires HTTP proxy for access in mainland china
HTTP_PROXY_HOST = "127.0.0.1"
HTTP_PROXY_PORT = "1087"

# Set PROXIES to None if you do not need proxy to access openAI
# PROXIES = None
PROXIES = {
    "http": f"http://{HTTP_PROXY_HOST}:{HTTP_PROXY_PORT}",
    "https": f"http://{HTTP_PROXY_HOST}:{HTTP_PROXY_PORT}",
}

# Directory for storing temporary files
TMP_DIR = Path("/tmp")

# ============== CONFIG =====================

app = Flask(__name__, template_folder='templates', static_folder='static')
Several_spaces_pattern = re.compile(r"\s+")


@app.route('/')
def index():
    # Get hostname
    hostname = socket.gethostname()

    # Get local ip
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
    except Exception as e:
        local_ip = socket.gethostbyname(hostname + ".local")
    finally:
        if s:
            s.close()
    api_key = load_api_key()

    return render_template(
        'index.html', hostname=hostname, local_ip=local_ip, api_key=api_key,
    )


@app.route('/submit-data',  methods=['POST'])
def submit():
    form = request.form

    # Set up your OpenAI API key
    api_key = form['api-key']
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
    }

    if form['input-text'] == "":
        revised_text = "Please input the paragraph for revision in the left."
    elif not api_key.startswith("sk-"):
        revised_text = "Please make sure the OpenAI API key is correct."
    else:
        print(f"Waiting for response from openai")
        revised_text = revise_paragraph(
            headers, form['title-text'], form['keywords-text'], form['section-text'].lower(),
            form['input-text'], form['model-text'],
        )

    return jsonify({"status": "Success", "revised": revised_text})


@app.route('/download-file', methods=['POST', 'GET'])
def download():
    form = request.form
    time_stamp = datetime.now().strftime("%Y%m%d-%H%H%S")
    revised_file = TMP_DIR / f"ManuGPT.{time_stamp}.docx"

    print(f"Saving revised docx {revised_file}")
    save_docx(form['input-text'], form['output-text'], form['model-text'], str(revised_file))

    return send_file(str(revised_file), as_attachment=True)


def get_prompt(paragraph_text: str, section_name: str, title: str, keywords: str, edit_endpoint=False):
    """
    From: https://github.com/manubot/manubot-ai-editor/blob/main/libs/manubot_ai_editor/models.py

    Returns the prompt to be used for the revision of a paragraph that
    belongs to a given section. There are three types of prompts according
    to the section: Abstract, Introduction, Methods, and the rest (i.e.
    Results, Discussion, etc.).
    Args:
        paragraph_text: text of the paragraph to revise.
        section_name: name of the section the paragraph belongs to.
    Returns:
        If self.edit_endpoint is False, then returns a string with the prompt to be used by the model for the revision of the paragraph.
        It contains two paragraphs of text: the command for the model
        ("Revise...") and the paragraph to revise.
        If self.edit_endpoint is True, then returns a tuple with two strings:
         1) the instructions to be used by the model for the revision of the paragraph,
         2) the paragraph to revise.
    """
    if section_name in ("abstract",):
        prompt = f"""
            Revise the following paragraph from the {section_name.capitalize()} of an academic paper (with the title '{title}' and keywords '{keywords}')
            so the research problem/question is clear,
               the solution proposed is clear,
               the text grammar is correct, spelling errors are fixed,
               and the text is in active voice and has a clear sentence structure
        """
    elif section_name in ("introduction", "discussion"):
        prompt = f"""
            Revise the following paragraph from the {section_name.capitalize()} section of an academic paper (with the title '{title}' and keywords '{keywords}')
            so
               most of the citations to other academic papers are kept,
               the text minimizes the use of jargon,
               the text grammar is correct, spelling errors are fixed,
               and the text has a clear sentence structure
        """
    elif section_name in ("results",):
        prompt = f"""
            Revise the following paragraph from the {section_name.capitalize()} section of an academic paper (with the title '{title}' and keywords '{keywords}')
            so
               most references to figures and tables are kept,
               the details are enough to clearly explain the outcomes,
               sentences are concise and to the point,
               the text minimizes the use of jargon,
               the text grammar is correct, spelling errors are fixed,
               and the text has a clear sentence structure
        """
    elif section_name in ("methods",):
        equation_definition = r"$$ ... $$ {#id}"
        revise_sentence = f"""
            Revise the paragraph(s) below from
            the {section_name.capitalize()} section of an academic paper
            (with the title '{title}' and keywords '{keywords}')
        """.strip()

        prompt = f"""
            {revise_sentence}
            so
               most of the citations to other academic papers are kept,
               most of the technical details are kept,
               most references to equations (such as "Equation (@id)") are kept,
               all equations definitions (such as '{equation_definition}') are included with newlines before and after,
               the most important symbols in equations are defined,
               spelling errors are fixed, the text grammar is correct,
               and the text has a clear sentence structure
        """.strip()
    else:
        prompt = f"""
            Revise the following paragraph from the {section_name.capitalize()} section of an academic paper (with the title '{title}' and keywords '{keywords}')
            so
               the text minimizes the use of jargon,
               the text grammar is correct, spelling errors are fixed,
               and the text has a clear sentence structure
        """

    prompt = Several_spaces_pattern.sub(" ", prompt).strip()

    if edit_endpoint is False:
        return f"{prompt}.\n\n{paragraph_text.strip()}"
    else:
        prompt = prompt.replace("the following paragraph", "this paragraph")
        return f"{prompt}.", paragraph_text.strip()


def revise_paragraph(headers, title, keywords, section, text, model_name):
    """
    Revise your paragraph using openAI API
    :param headers:
    :param title:
    :param keywords:
    :param section:
    :param text:
    :param edit_endpoint:
    :return:
    """
    if model_name in ['text-davinci-003', 'gpt-3.5-turbo']:
        edit_endpoint = False
    else:
        edit_endpoint = True

    prompt = get_prompt(text, section, title, keywords, edit_endpoint=edit_endpoint)

    # Prepare request data
    if model_name == 'text-davinci-003':
        url = 'https://api.openai.com/v1/completions'
        json_data = {'model': model_name, 'prompt': prompt, 'max_tokens': 1024, 'temperature': 0.5}
    elif model_name == 'text-davinci-edit-001':
        url = 'https://api.openai.com/v1/edits'
        json_data = {'model': model_name, 'input': prompt[1], 'instruction': prompt[0]}
    elif model_name == 'gpt-3.5-turbo':
        url = 'https://api.openai.com/v1/chat/completions'
        json_data = {'model': model_name, 'messages': [{'role': 'user', 'content': prompt}]}
    else:
        print(f"Unsupported model name for {model_name}")

    # Make request
    if PROXIES is not None:
        response = requests.post(url, headers=headers, json=json_data, proxies=PROXIES)
    else:
        response = requests.post(url, headers=headers, json=json_data)

    ret = json.loads(response.text.strip())

    if model_name in ['text-davinci-003', 'text-davinci-edit-001']:
        text = ret['choices'][0]['text'].strip()
    else:
        text = ret['choices'][0]['message']['content']

    return text


def save_docx(raw_text, revised_text, model_name, out_file):
    """
    Save revised paragraph to docx files and record the changes
    :param raw_text: str,
        input text from the user
    :param revised_text: str,
        revised text by openAI
    :param model_name: str,
        name of model, which will be also used as the author of revised changes in output docx.
    :param out_file: str,
        path to output docx
    """
    original_doc = aw.Document()
    builder = aw.DocumentBuilder(original_doc)
    builder.writeln(raw_text)

    revised_doc = aw.Document()
    builder = aw.DocumentBuilder(revised_doc)
    builder.writeln(revised_text)

    original_doc.compare(revised_doc, model_name, datetime.now())
    original_doc.save(out_file)


def load_api_key():
    key_file = Path.home() / ".openai_key"
    if key_file.exists():
        with open(key_file, 'r') as f:
            return f.readline().rstrip()
    else:
        return ""


if __name__ == '__main__':
    app.run(debug=False, host=FLASK_HOST, port=FLASK_PORT)
