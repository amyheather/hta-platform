# hta-platform

The HTA Platform is a Python and Streamlit-based application that supports Health Technology Assessment data extraction workflows. It combines web scraping, PDF table extraction and Retrieval-Augmented Generation (RAG) document search into a single application.

This platform was developed by **Shantanu Fulaware** in their dissertation project for their MSc Health Data Science degree at the University of Exeter. It was developed with support from **Dawn Lee** and **Saul Stevens** in the Peninsula Technology Assessment Group (PenTAG) and **Thomas Monks** in the Peninsula Collaboration for Health Operational Research and Development group (PenCHORD).


## Set-up

1. Install Python environment.

```
conda env create --file hta-platform/environment-vscode.yml
conda activate nice-hta-platform-dev
```

2. Install Ghostscript.

*  **Windows:** Download and install from https://ghostscript.com/index.html.
* **macOS:** `brew install ghostscript`.
* **Linux:** `sudo apt-get install ghostscript`.

3. Install Ollama, either clicking download link in https://ollama.com/download or running:

* **Windows:** `irm https://ollama.com/install.ps1 | iex`
* **macOS:** `curl -fsSL https://ollama.com/install.sh | sh`
* **Linux:** `curl -fsSL https://ollama.com/install.sh | sh`