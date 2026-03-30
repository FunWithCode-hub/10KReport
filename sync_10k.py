import requests
from os import listdir
from playwright.sync_api import sync_playwright


def html_to_pdf(html_text, output_path):
    # Launch a headless Chromium browser, load the HTML content, and export it as a PDF
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_text, wait_until="networkidle")
        page.pdf(path=output_path, format="A4", print_background=True)
        browser.close()


# Using Companies as a dictionary here, key as a company name, and value as SEC EDGAR CIK, CIKs are found here: https://www.sec.gov/search-filings/cik-lookup
companies = {
    "Apple": "0000320193",
    "Meta": "0001326801",
    "Alphabet": "0001652044",
    "Amazon": "0001018724",
    "Netflix": "0001065280",
    "Goldman Sachs": "0000886982"
}

# The SEC EDGAR API requires a User-Agent header to identify the caller
headers = {"User-Agent": "abc@example.com"}

# The form filing type 10-K is our interest here
form = "10-K"

# Looping over each company, we find the latest 10-K filing and save it as a PDF
for company, cik in companies.items():
    # Fetch the company's full submission history from SEC EDGAR, as https://data.sec.gov/submissions/CIK##########.json
    submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    data = requests.get(submissions_url, headers=headers).json()

    # The "recent" key contains arrays of filings metadata (form type, accession number,filing date, primary document name, etc.)
    recent = data.get("filings", {}).get("recent", {})

    # Finding the indices of all 10-K filings in the recent submissions list
    ten_k_indexes = [index for (index, t) in enumerate(recent["form"]) if t == form]

    # Building a list of dict with accession number, filing date, and primary document name for each 10-K
    ten_k_reports = list(
        map(
            lambda r: {
                "acc_no": recent["accessionNumber"][r],
                "date": recent["filingDate"][r],
                "doc": recent["primaryDocument"][r],
            },
            ten_k_indexes,
        )
    )

    # We select the most recent 10-K by comparing filing dates
    latest_ten_k_report = max(ten_k_reports, key=lambda l: l["date"])

    # Here, we remove dashes from the accession number to build the EDGAR archive URL
    acc = latest_ten_k_report["acc_no"].replace("-", "")
    doc = latest_ten_k_report["doc"]
    latest_date = latest_ten_k_report["date"]
    # We are just using the current directory to save the PDF files
    existing_files = listdir()
    pdf_filename = f"{company}_10K_{latest_date}.pdf"

    if pdf_filename not in existing_files:
        # Construct the direct URL to download the latest 10-K filing
        ten_k_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"
        print(f"Downloading filing from: {ten_k_url}")

        html = requests.get(ten_k_url, headers=headers).text

        # Convert the HTML filing to PDF 
        html_to_pdf(html, pdf_filename)
        print(f"Saved PDF as: {pdf_filename}")
    else:
        print(f"File {pdf_filename} already exists. Skipping download.")
