import streamlit as st

from src.data_loader import get_dataset_stats


def _ms(name: str, size: str = "1.15em") -> str:
    """Inline Material Symbols Outlined span for use in unsafe_allow_html markdown."""
    return (
        f'<span class="material-symbols-outlined" '
        f'style="font-size:{size};vertical-align:middle;margin-right:4px;">{name}</span>'
    )


def render():
    st.header("About the CRPD Dashboard")

    _s = get_dataset_stats()

    st.markdown(
        f"### {_ms('assignment')} Project Overview",
        unsafe_allow_html=True,
    )
    st.write(
        f"This dashboard provides comprehensive analysis of CRPD (Convention on the Rights of "
        f"Persons with Disabilities) implementation across {_s['n_countries']} countries, "
        f"spanning {_s['year_min']}–{_s['year_max']} with {_s['n_docs']} documents analyzed."
    )

    st.markdown(
        f"""
        <div class="about-info-box" style="border-left:4px solid #005bbb;
            background:linear-gradient(135deg,#EEF4FF,#F8FAFF);margin:1.5rem 0;">
            <h4 style="color:#003F87;margin-top:0;">
                {_ms("verified_user")} Open Data Commitment
            </h4>
            <p style="font-size:0.95rem;color:#191C1F;line-height:1.75;margin:0;">
                The CRPD Disability Rights Data Dashboard is built on public United Nations
                treaty body documents. All dashboard visualizations, country profiles, article
                coverage analysis, reporting timelines, and comparative tools are free and
                always will be. The Extended tier provides supplementary AI-powered research
                assistance only — it never gates access to treaty data or analytical features.
                This commitment reflects CRPD Articles 9 (Accessibility) and 21 (Freedom of
                Expression and Access to Information).
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown(
        f"### {_ms('menu_book')} The UN CRPD Reporting Cycle",
        unsafe_allow_html=True,
    )
    st.write("""
    This dashboard captures the **complete dialogue** between State Parties and the
    independent Committee on the Rights of Persons with Disabilities (sitting at the
    UN Office of the High Commissioner for Human Rights in Geneva). Our analysis includes
    **five document types** across the full reporting cycle:
    """)

    st.markdown("""
    1. **State Party Reports** — Countries' self-assessment of CRPD implementation
    2. **List of Issues** — Committee's questions and concerns about the report
    3. **Written Responses** — State Parties' replies to the Committee's questions
    4. **Concluding Observations** — Committee's final assessment and recommendations
    5. **Responses to Concluding Observations** — State Parties' follow-up actions
    """)

    st.info("""
    💡 **Why this matters:** By analyzing documents across the entire reporting cycle,
    we can track not just what countries claim, but how the Committee responds, what
    questions they raise, and how nations follow through — providing unprecedented insight
    into the real-world implementation of disability rights.
    """)

    st.markdown("---")
    st.markdown(
        f"### {_ms('biotech')} Methodology",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            f"""
        <div class="about-info-box">
            <h4>{_ms("bar_chart")} Text Analysis</h4>
            <ul style="line-height: 1.8;">
                <li><strong>TF-IDF Analysis:</strong> Identifies distinctive terminology</li>
                <li><strong>Keyword Frequency:</strong> Tracks recurring themes</li>
                <li><strong>Article Mapping:</strong> Uses keyword dictionaries</li>
            </ul>
        </div>

        <div class="about-info-box" style="margin-top: 20px;">
            <h4>{_ms("sync_alt")} Model Shift Analysis</h4>
            <ul style="line-height: 1.8;">
                <li>Medical to rights-based evolution tracking</li>
                <li>Temporal and regional variations</li>
                <li>Actor-specific emphasis patterns</li>
            </ul>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
        <div class="about-info-box">
            <h4>{_ms("public")} Comparative Analysis</h4>
            <ul style="line-height: 1.8;">
                <li>Cross-country reporting patterns</li>
                <li>State vs. Committee emphasis</li>
                <li>Regional and temporal trends</li>
                <li>Five-stage cycle dynamics</li>
            </ul>
        </div>

        <div class="about-info-box" style="margin-top: 20px;">
            <h4>{_ms("rocket_launch")} Future Enhancements</h4>
            <ul style="line-height: 1.8;">
                <li>World Bank Disability Data Hub integration</li>
                <li>Disability Data Initiative metrics</li>
                <li>Quantitative outcome correlations</li>
            </ul>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown(
        f"### {_ms('storage')} Data Sources",
        unsafe_allow_html=True,
    )

    st.markdown("""
    **PRIMARY SOURCE:** UN Treaty Body Database
    All documents sourced from official UN communications between State Parties and the Committee.

    **FUTURE INTEGRATION:**
    - **World Bank Disability Data Hub:** Quantitative indicators on disability prevalence, outcomes
    - **Disability Data Initiative:** Complementary datasets on implementation and impact
    """)

    st.markdown("---")
    st.markdown(
        f"### {_ms('build')} Technical Stack",
        unsafe_allow_html=True,
    )
    st.write("""
    - **Framework**: Streamlit + Python
    - **Visualization**: Plotly Express
    - **NLP**: scikit-learn (TF-IDF)
    - **Data Processing**: Pandas, NumPy
    - **Deployment**: Posit Connect Cloud
    """)

    st.markdown("---")
    st.markdown(
        f"### {_ms('groups')} Research Team",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **Principal Investigator**
        Dr. Derrick L. Cogburn
        Professor of Environment, Development & Health
        Professor of Information Technology & Analytics
        UNESCO Associate Chair, Transnational Challenges and Governance
        Executive Director, Institute on Disability and Public Policy (IDPP)
        American University, School of International Service

        **Co-Investigator**
        Dr. Keiko Shikako
        Canada Research Chair in Childhood Disabilities: Participation and Knowledge Translation
        Associate Professor, McGill University | School of Physical and Occupational Therapy
        Associate Member, Department of Ethics, Equity and Policy | MUHC-RI | CanChild

        **Research Team Members**
        - Mr. Conrad Linus Muhirwe
        - Mr. John Dylan Bustillo
        - Ms. Anja Herman, American University
        - Ms. Ananya Chandra, McGill University
        - Ms. Sharon Wanyana, American University
        - Ms. Olivia Prezioso, Northeastern University
        - Ms. Sofia Torres
        - Mr. Juan David Lopez
        - Ms. Juliana Woods, American University
        - Ms. Rachi Adhikari, American University

        **Former Research Team Members**
        - Mr. Theodore Andrew Ochieng, American University
        - Ms. Mina Aydin, University of Virginia
        """)

    with col2:
        st.markdown("""
        **Project Information**
        Developed: 2024-2026
        Version: 7.1
        Last Updated: March 2026

        **Citation**
        Cogburn, D., et al (2025). *CRPD Disability Rights Data Dashboard*.
        Institute on Disability and Public Policy, American University.

        **Related Open Access Publication:**
        Cogburn, D; Ochieng, T.; Shikako, K.; Woods, J.; and Aydin, M. (2025)
        Uncovering policy priorities for disability inclusion: NLP and LLM approaches
        to analyzing CRPD State reports, *Data & Policy*, Cambridge University Press.
        DOI: https://doi.org/10.1017/dap.2025.10017
        """)

    st.markdown("---")
    st.info("""
    💡 **For Questions or Collaboration**: This dashboard is designed to support research,
    advocacy, and policy analysis related to disability rights and the CRPD. For inquiries
    about the data, methodology, or potential collaborations, please contact IDPP at American University.
    """)
