# CRPD Disability Rights Data Dashboard

An interactive data dashboard for analyzing implementation of the UN Convention on the Rights of Persons with Disabilities (CRPD) across 143 countries.

## Project Overview
This dashboard provides researchers, policymakers, and advocates with tools to explore CRPD reporting patterns, compliance trends, and cross-country comparisons.

## Features
- Interactive world map with country-level data
- Temporal analysis (2010-2025)
- Comparative analysis tools
- Document type explorer
- Data export capabilities (removed for now for freemium; defered for premium).

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

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines, including branching, PR, testing, and deployment.

## Current Team Members
- Dr. Derrick Cogburn, American University
- Dr. Keiko Shikako, McGill University
- Mr. John Dylan Bustillo, American University
- Mr. Conrad Linus Muhirwe, American University
- Ms. Sharon Wanyana, American University
- Ms. Sofia Torres
- Mr. Juan David Lopez
- Ms. Olivia Prezioso, Northeastern University
- Institute on Disability and Public Policy (IDPP)

## Former Team Members
- Ms. Juliana Woods, American University
- Ms. Rachi Adhikari, American University
- Mr. Theodore Andrew Ochieng, American University

## License
This work is licensed under a [Creative Commons Attribution-NonCommercial 4.0 International License](https://creativecommons.org/licenses/by-nc/4.0/).


## Citation
Cogburn, D. et al (2026). CRPD Disability Rights Data Dashboard. Institute on Disability and Public Policy, American University. https://idpp.connect.posit.cloud/crpd-dashboard
