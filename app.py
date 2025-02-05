
import gradio as gr
from pypdf import PdfReader
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores.qdrant import Qdrant
import sqlite3
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from starlette.responses import HTMLResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# OpenAI Key
import os
os.environ["OPENAI_API_KEY"] = "secret- key"

# ----------------------------------------------------------------------------------

"""Delete cache """

# Delete cache function for app run
def delete_cache_app_run():

    # Check and delete if SQLite DB exists -- Added by Riddhiman
    if os.path.exists('./content/text_chunks_and_pages.db'):
        os.remove('./content/text_chunks_and_pages.db')

    # Check and delete if generated PDF exists -- Added by Riddhiman
    if os.path.exists('./static/report.pdf'):
        os.remove('./static/report.pdf')
        
    return "Database and report cache deleted. Please reload the page."

# Delete cache on app run
delete_cache_app_run()

# ----------------------------------------------------------------------------------

# Location of the SQLite database file
db_file_path = './content/text_chunks_and_pages.db'

# Dictionary to store text chunks and their corresponding pages
raw_text = ''
text_pages_dict = {}

# Chat history
chat_history = []

# Function to process uploaded PDFs and store in SQLite
def process_pdfs(files):
    from io import BytesIO
    global raw_text, text_pages_dict,chat_history

    # Clear previous data
    raw_text = ''
    text_pages_dict = {}
    chat_history = []

    # Process each uploaded PDF file
    for filepath in files:
        # Read the file contents into a BytesIO object
        with open(filepath, "rb") as fh:
            contents = BytesIO(fh.read())

        try:
            pdf_reader = PdfReader(contents)
            for i, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text:
                    raw_text += text
                    text_splitter = CharacterTextSplitter(
                        separator=".",
                        chunk_size=1000,
                        chunk_overlap=200,
                        length_function=len,
                    )
                    # Split the raw text
                    texts = text_splitter.split_text(text)
                    # Store text chunks and their corresponding pages in the dictionary
                    for text_chunk in texts:
                        cleaned_text = text_chunk.replace('\n', ' ')
                        if cleaned_text in text_pages_dict:
                            text_pages_dict[cleaned_text].append(i + 1)
                        else:
                            text_pages_dict[cleaned_text] = [i + 1]

        finally:
            # No need to close the BytesIO object
            pass

    # Ensure the database file does not exist
    if Path(db_file_path).exists():
        raise FileExistsError(f"The database file '{db_file_path}' already exists. Please choose a different name.")

    # Create a connection to the SQLite database
    conn = sqlite3.connect(db_file_path)

    # Create a cursor object to interact with the database
    cursor = conn.cursor()

    # Create a table to store text chunks and page numbers
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS text_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text_chunk TEXT NOT NULL,
            page_numbers TEXT NOT NULL
        )
    ''')

    # Commit the changes to the database
    conn.commit()

    # Insert data into the table
    for text_chunk, page_numbers in text_pages_dict.items():
        page_numbers_str = ', '.join(map(str, page_numbers))
        cursor.execute('INSERT INTO text_chunks (text_chunk, page_numbers) VALUES (?, ?)', (text_chunk, page_numbers_str))

    # Commit the changes to the database
    conn.commit()

    # Close the cursor and connection
    cursor.close()
    conn.close()

    return "PDFs processed successfully."

# -----------------------------------------------------------------------------------

"""Function for PDF generation"""

def save_to_pdf(question, answer):
    
    # Create a PDF file
    pdf_file_path = "./static/report.pdf"

    # Create a PDF canvas
    c = canvas.Canvas(pdf_file_path)
   
    # Set font and size
    c.setFont("Helvetica", 12)

    # Write the question to the PDF
    c.drawString(10, 800, "Question:")
    
    text = str(question).split()
    words = 10
    height = 780
    
    for line in [' '.join(text[i:i+words]) for i in range(0, len(text), words)]:
        c.drawString(10, height, line)
        height -= 15

    # Write the answer to the PDF
    c.drawString(10, 750, "Answer:")
    
    text = str(answer).split()
    words = 10
    height = 730
    
    for line in [' '.join(text[i:i+words]) for i in range(0, len(text), words)]:
        c.drawString(10, height, line)
        height -= 15

    # Show pages
    c.showPage()

    # Save the canvas to the PDF file
    c.save()

    return pdf_file_path

#-------------------------------------------------------------------------------------

"""Function to answer questions and get related documents"""

def answer_question(question, num="10"):
    global text_pages_dict,chat_history

    # Download embeddings from OpenAI
    embeddings = OpenAIEmbeddings()

    # Use the text chunks from the processed PDF
    texts = list(text_pages_dict.keys())
    
    # Create a Qdrant index named 'docsearch'
    docsearch = Qdrant.from_texts(
        texts,
        embeddings,
        location=":memory:",  # Local mode with in-memory storage only
        collection_name="MyCollection"
    )

    from langchain.chains.question_answering import load_qa_chain
    from langchain_openai import OpenAI

    chain = load_qa_chain(OpenAI(), chain_type="stuff")

    # Retrieve documents from Qdrant with relevance scores
    k = int(num)
    docs_with_scores = docsearch.similarity_search_with_score(question, k=k)

    # Create the output HTML for related documents
    related_docs_html = "<h3><b>Related References:</b></h3><br />"
    for i, (doc, score) in enumerate(docs_with_scores):
        # Extract text chunk from the document
        page_content = doc.page_content
        cleaned_text = page_content.replace('\n', ' ')  # Replace newlines with spaces for readability

        # Query the database for the text chunk and page numbers
        conn = sqlite3.connect(db_file_path)
        cursor = conn.cursor()
        cursor.execute('SELECT text_chunk, page_numbers FROM text_chunks WHERE text_chunk = ?', (cleaned_text,))
        result = cursor.fetchone()

        if result:
            text_chunk, page_numbers_str = result
            page_numbers = [int(num) for num in page_numbers_str.split(', ')]
            page_numbers_str = ', '.join(map(str, page_numbers))
            related_docs_html += f"<p><b>Reference {i + 1}:</b><br />{page_content}</p>"
            #related_docs_html += f"<p><b>Page Numbers:</b> {page_numbers_str}</p>"
            related_docs_html += f"<p><b>Relevance Score:</b> {score}</p><br>"
        else:
            related_docs_html += f"<p><b>Reference {i + 1}:</b> {page_content}</p>"
            related_docs_html += f"<p><b>Text Chunk not found in the database.</b></p><br>"

        # Close the cursor and connection
        cursor.close()
        conn.close()

    # Run the QA chain with the retrieved documents and query
    docs_for_qa = docsearch.similarity_search(question, k=k)
    answer = chain.run(input_documents=docs_for_qa, question=question)
    pdf_file_path = save_to_pdf(question, answer)
    chat_history.append({"question": question, "answer": answer})

    return answer, related_docs_html, f"<a href='.{pdf_file_path}' download>Download PDF</a>"

# ------------------------------------------------------------------------------------

# Function to view chat history
def view_chat_history():
    global chat_history
    history_text = "<h2><b> </b></h2><br />"
    for entry in chat_history:
        history_text += f"<p><b>Question: </b> {entry['question']}<br /><b>Answer: </b> {entry['answer']}</p><br />"
    return history_text

# ------------------------------------------------------------------------------------

# Create the Gradio interface for answering questions
with gr.Blocks() as demo:
    with gr.Row():
        pdf_text=gr.HTML(value="<h1 style='margin-top: 1rem; margin-bottom: 1rem; text-align: center'>Document QA System</h1>")
    with gr.Row():
        pdf_text=gr.HTML(value="<h2 style='margin-top: 1rem; margin-bottom: 1rem'>Upload PDF</h2>")
    with gr.Row():
        files = gr.File(label="Upload PDFs", file_count="multiple", file_types=[".pdf"])
        iface_pdf_processing = gr.Interface(fn=process_pdfs, inputs=files, outputs=[gr.Textbox(label="Response")],allow_flagging="never")
    with gr.Row():
        pdf_text=gr.HTML(value="<h2 style='margin-top: 1rem; margin-bottom: 1rem'>Chat</h2>")
    with gr.Row():
        iface_qa = gr.Interface(fn=answer_question, inputs=[gr.Textbox(label="Enter your question here"), 
                                                            gr.Textbox(label="Number of references to be shown", value="3")], 
                                                    outputs=[gr.Textbox(label="Answers"),
                                                             "html","html"
                                                             ],
                                                            allow_flagging="never")
    with gr.Row():
        pdf_text=gr.HTML(value="<h2 style='margin-top: 1rem; margin-bottom: 1rem'>Chat History</h2>") 
    with gr.Row():
        iface_chat_history = gr.Interface(fn=view_chat_history, inputs=None, outputs="html",allow_flagging="never")
    with gr.Row():
        pdf_text=gr.HTML(value="<h2 style='margin-top: 1rem; margin-bottom: 1rem'>Controls</h2>")
    with gr.Row():
        btn1 = gr.Button(value="Delete Database and Report Cache", variant="stop")
        output = gr.Textbox(label="Status", value="App loaded.")
        btn1.click(fn=delete_cache_app_run, outputs=output)
        btn2 = gr.Button(value="Reload App", variant="stop")
        btn2.click(None, js="window.location.reload()")

# -------------------------------------------------------------------------------------

"""FastAPI application """        
        
# Import FastAPI libraries
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi_login import LoginManager
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles

# Create app with basic HTTP auth
class NotAuthenticatedException(Exception):
    pass

app = FastAPI()
security = HTTPBasic()

SECRET = "78797gdgfdh0gjhfhfkkjkgaqeqazogdgkosjvr9"
manager = LoginManager(SECRET, '/', use_cookie=False, custom_exception=NotAuthenticatedException)

# Set credentials and response
@app.exception_handler(NotAuthenticatedException)
def auth_exception_handler(request: Request, exc: NotAuthenticatedException):
    return RedirectResponse(url='/')

@app.get('/')
def login(data: Annotated[HTTPBasicCredentials, Depends(security)]):

    if not (data.username == "stanleyjobson") or not (data.password == "swordfish"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    response = RedirectResponse(url="/app/", status_code=status.HTTP_302_FOUND)
    return response

@app.get('/app')
def protected_route(user=Depends(manager)):
    return {'user': user}
  
# ---------------------------------------------------------------------------------------

app = gr.mount_gradio_app(app, demo, path="/app")
app.mount("/static", StaticFiles(directory="static"), name="static")
