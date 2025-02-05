# Large-Language-Models
Langchain  and vector  Data base  created in  Gradio interfact  for Query  system for local office use check invoices, FAQ etc
Large-Language-Models

Overview

This project is designed to process and retrieve relevant answers from FAQs and documents in PDF format. It supports the company’s internal document management by enabling efficient search and retrieval of information related to business transactions, purchase orders, invoices, agreements, and other commercial documents. The system is accessible only to company employees.

Features

FAQ Retrieval: Fetches relevant answers from documents containing frequently asked questions.

PDF Support: Exclusively works with PDF documents.

Secure Access: Designed for internal use, ensuring that documents are accessible only to authorized employees.

Query System: Users can search for specific invoices, agreements, or other documents for particular purposes.

Tech Stack

Framework: LangChain

Database: SQLite (Vector Database)

Interface: Gradio

Libraries/Tools:

PyTorch

sqlite3

OpenAI API (ChatGPT)

How It Works

PDF Input: Users upload PDFs containing FAQs or other commercial documents.

Text Processing: LangChain processes the text, storing it in SQLite as vector embeddings.

Query Execution: Using the OpenAI API, the system matches user queries with stored vectors to retrieve relevant answers.

Gradio Interface: Provides an intuitive UI for uploading documents, entering queries, and viewing results.

Usage

Upload Documents: Upload PDFs containing FAQs or other commercial documents.

Search Queries: Use the Gradio interface to type queries and retrieve relevant information.

Future Improvements

Add support for additional file formats (e.g., Word, Excel).

Integrate advanced search filters for more granular queries.

Implement multi-language support for documents.

Contribution

Contributions are welcome! Please fork the repository and submit a pull request with detailed explanations of changes.
