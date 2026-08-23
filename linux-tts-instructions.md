# Linux Instructions for TTS Installation

This document describes how to install the required TTS voice model on Linux and optionally configure a local command-line script for converting PDF documents to speech.

## 1. Download Voice Models

Navigate to the Piper voice model directory:

```bash
cd ~/.local/share/piper-voices
```

Download the high-quality British English voice model:

```bash
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/cori/high/en_GB-cori-high.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/cori/high/en_GB-cori-high.onnx.json
```

## 2. Optional: Test TTS from the Command Line

The following steps configure a command-line utility that extracts text from a PDF and sends it directly to Piper for speech synthesis.

## 3. Install Required Libraries

Install `poppler-utils`, which provides the `pdftotext` command:

```bash
sudo apt install poppler-utils
```

The script also requires:

*   piper
*   aplay
*   A Piper voice model

## 4. Create the PDF-to-Speech Script

Create the script:

```bash
nano ~/.local/bin/pdf2speech.sh
```

Add the following content to `~/.local/share/piper-voices/en_GB-alan-medium.onnx` variable is configured in line above, verify path if different from downloaded model (see Section 1 and Troubleshooting):

```bash
#!/usr/bin/env bash

# Exit immediately if a command fails
set -e

# Configuration
VOICE_MODEL="$HOME/.local/share/piper-voices/en_GB-alan-medium.onnx"

# Arguments
PDF_FILE="$1"
START_PAGE="${2:-1}"  # Defaults to page 1 if not specified
END_PAGE="$3"         # Optional end page

# Sanity checks
if [ -z "$PDF_FILE" ] || [ ! -f "$PDF_FILE" ]; then
    echo "Error: PDF file not found!"
    echo "Usage: pdf2speech <pdf_file> [start_page] [end_page]"
    exit 1
fi

if [ ! -f "$VOICE_MODEL" ]; then
    echo "Error: Voice model not found at $VOICE_MODEL"
    exit 1
fi

# Build page arguments for pdftotext
PAGE_ARGS="-f $START_PAGE"
if [ -n "$END_PAGE" ]; then
    PAGE_ARGS="$PAGE_ARGS -l $END_PAGE"
    echo "Reading '$PDF_FILE' from page $START_PAGE to $END_PAGE..."
else
    echo "Reading '$PDF_FILE' starting from page $START_PAGE..."
fi

# Extract text and send directly to Piper -> Audio Player
pdftotext $PAGE_ARGS "$PDF_FILE" - | \
  piper --model "$VOICE_MODEL" --output_raw | \
  aplay -r 22050 -f S16_LE -t raw -
```

## 5. Make the Script Executable

Make the script executable:

```bash
chmod +x ~/.local/bin/pdf2speech.sh
```

## 6. Execute the Script

The command accepts the following arguments: `pdf2speech <pdf_file> [start_page] [end_page]`

For example:

```bash
pdf2speech /path/to/document.pdf 1 10
```


This reads pages 1 through 10 of the PDF.

To start from a specific page and continue to the end of the document:

```bash
pdf2speech /path/to/document.pdf 10
```

## 7. Test the Installation

Test the script with a PDF document:

```bash
pdf2speech /path/to/document.pdf
```


Test a specific page range:

```bash
pdf2speech /path/to/document.pdf 1 5
```


Test starting from a specific page and reading through to end:

```bash
pdf2speech /path/to/document.pdf 10
```


If the installation is configured correctly, the PDF text will be extracted using `pdftotext`, synthesized by Piper, and played through the system audio device using `aplay`.

## 8. Troubleshooting

### PDF File Not Found

If the specified PDF does not exist, the script reports:

```bash
Error: PDF file not found!
Usage: pdf2speech <pdf_file> [start_page] [end_page]
```


Verify that the PDF path is correct:

```bash
ls -l /path/to/document.pdf
```

### Voice Model Not Found

If the configured voice model cannot be found, the script reports:

```bash
Error: Voice model not found at <voice-model-path>
```

Verify that the voice model exists:

```bash
ls -l ~/.local/share/piper-voices/
```


**Important:** The voice model downloaded in Section 1 is `en_GB-cori-high.onnx`, while the example script currently references `en_GB-alan-medium.onnx`.

Update the `VOICE_MODEL` variable in the script so that it points to the model you actually installed. For example:

```bash
VOICE_MODEL="$HOME/.local/share/piper-voices/en_GB-cori-high.onnx"
```


Verify pdftotext

Check that `pdftotext` is installed:

```bash
which pdftotext
```


You can also check its version:

```bash
pdftotext -v
```


### Verify Piper

Check that Piper is available:

```bash
which piper
```

### Verify aplay

Check that `aplay` is available:

```bash
which aplay
```

## 9. Complete Example

Once everything is installed, the typical workflow is:

Navigate to models and install voice model files:

```bash
cd ~/.local/share/piper-voices

wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/cori/high/en_GB-cori-high.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/cori/high/en_GB-cori-high.onnx.json
```


Install the PDF text extraction utility:

```bash
sudo apt install poppler-utils
```

Create the script (`nano ~/.local/bin/pdf2speech.sh`): (See Section 4)

Make it executable:

```bash
chmod +x ~/.local/bin/pdf2speech.sh
```

Run it:

```bash
pdf2speech /path/to/document.pdf 1 10
```


The expected flow is: `PDF document -> pdftotext -> Piper -> aplay -> Audio output`