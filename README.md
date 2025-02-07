# Auto-Scroller README

# Installing Tesseract OCR

Tesseract OCR is an open-source optical character recognition (OCR) engine. This guide will help you install Tesseract OCR on Windows and configure it for use with Python.

## Step 1: Download Tesseract OCR

1. Visit the official Tesseract OCR repository on GitHub:
   - [Tesseract OCR GitHub Releases](https://github.com/UB-Mannheim/tesseract/wiki)
2. Download the latest Windows installer (`.exe` file) from the "UB Mannheim" builds section.
3. Save the file to your computer.

## Step 2: Install Tesseract OCR

1. Run the downloaded `.exe` file.
2. Follow the installation wizard:
   - Choose an installation path (e.g., `E:\Tesseract-OCR\`).
   - Select "Additional Language Data" if needed.
   - Click "Install" and wait for the process to complete.

## Step 3: Install Python Dependencies

1. Ensure you have Python installed. You can check by running:
   ```sh
   python --version
   ```
2. Install the required Python libraries using `pip` and `requirements.txt`:
   ```sh
   pip install -r requirements.txt
   ```

## Step 4: Configure Tesseract in Python

Now, open the app 

## Additional Resources
- [Tesseract OCR Documentation](https://github.com/tesseract-ocr/tesseract)
- [Pytesseract Documentation](https://pypi.org/project/pytesseract/)


## Why I Made This Thing

Honestly, I was just too annoyed to scroll manually. I mean, who hasn't been there? You're trying to read a manhwa (or manga), and your finger gets tired from scrolling. Yeah, it's a real problem.

So, I made this auto-scroller thingy. It's still early access (version 0.2, baby!), but it gets the job done.

## What It Can Do

This app can:

* Auto-scroll for you, so you don't have to lift a finger (literally)
* Use OCR (Optical Character Recognition) to detect text and adjust scrolling speed accordingly
* Let you select a screen region for OCR, so it doesn't accidentally read other words
* Start and stop auto-scrolling with a simple mouse click or key press

## Features

* Adjustable scrolling speed (because, let's face it, sometimes you need to slow down or speed up)
* Customizable OCR region (because, you know, not everyone wants to read the whole screen)

## Known Issues

* It's still early access, so there might be some bugs (sorry 🥺)
* The app might not work perfectly with all screen resolutions or orientations (working on it, though!)

## Future Plans

* Add more features (duh!)
* Improve performance and stability (yawn, but necessary)
* Make it look prettier (because, let's face it, looks matter)

## How to Use

1. Run the app (obviously)
2. Select a screen region for OCR (if you want to)
3. Click the "Start Auto-Scroll" button (or press the middle mouse button, or press a key... you get the idea)
4. Enjoy the auto-scrolling goodness!

## Contributing

If you want to help make this app better, feel free to contribute! Just fork the repo, make some changes, and submit a pull request. Easy peasy.

## License

This app is licensed under the MIT License. Because, why not?

Now, go forth and auto-scroll like a pro!