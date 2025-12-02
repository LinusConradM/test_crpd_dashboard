# CRPD Disability Rights Data Dashboard

An interactive data dashboard for analyzing implementation of the UN Convention on the Rights of Persons with Disabilities (CRPD) across 143 countries.

## Project Overview
This dashboard provides researchers, policymakers, and advocates with tools to explore CRPD reporting patterns, compliance trends, and cross-country comparisons.

## Features
- Interactive world map with country-level data
- Temporal analysis (2010-2025)
- Comparative analysis tools
- Document type explorer
- Data export capabilities

## Data
- **Source**: UN Treaty Body Database
- **Period**: 2010-2025
- **Documents**: 506 reports across 143 countries
- **Regions**: 6 global regions

## Project Structure
```
crpd-dashboard/
├── app.py                  # Main Streamlit application
├── data/                   # Data files
├── src/                    # Source code modules
├── assets/                 # Static assets
└── docs/                   # Documentation
```

## Installation
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Live Dashboard
View the dashboard at: https://idpp.connect.posit.cloud/crpd-dashboard

## Contributing
See [docs/development_guide.md](docs/development_guide.md) for contribution guidelines.

## Team
- Dr. Derrick Cogburn, American University
- Dr. Keiko Shikako, McGill University
- Ms. Juliana Woods, American University
- Ms. Rachi Adhikari, American University
- Mr. Theodore Andrew Ochieng, American University
- Institute on Disability and Public Policy (IDPP)

## License
This work is licensed under a [Creative Commons Attribution-NonCommercial 4.0 International License](https://creativecommons.org/licenses/by-nc/4.0/).


## Citation
Cogburn, D. et al (2025). CRPD Disability Rights Data Dashboard. Institute on Disability and Public Policy, American University. https://idpp.connect.posit.cloud/crpd-dashboard