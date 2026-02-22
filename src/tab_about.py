import streamlit as st


def render():
    st.header("About the CRPD Dashboard")

    st.subheader("📋 Project Overview")
    st.write("""
    This dashboard provides comprehensive analysis of CRPD (Convention on the Rights of
    Persons with Disabilities) implementation across 143 countries, spanning 2010-2025
    with 506 documents analyzed.
    """)

    st.markdown("---")
    st.subheader("📚 The UN CRPD Reporting Cycle")
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
    st.subheader("🔬 Methodology")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="about-info-box">
            <h4>📊 Text Analysis</h4>
            <ul style="line-height: 1.8;">
                <li><strong>TF-IDF Analysis:</strong> Identifies distinctive terminology</li>
                <li><strong>Keyword Frequency:</strong> Tracks recurring themes</li>
                <li><strong>Article Mapping:</strong> Uses keyword dictionaries</li>
            </ul>
        </div>

        <div class="about-info-box" style="margin-top: 20px;">
            <h4>🔄 Model Shift Analysis</h4>
            <ul style="line-height: 1.8;">
                <li>Medical to rights-based evolution tracking</li>
                <li>Temporal and regional variations</li>
                <li>Actor-specific emphasis patterns</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="about-info-box">
            <h4>🌍 Comparative Analysis</h4>
            <ul style="line-height: 1.8;">
                <li>Cross-country reporting patterns</li>
                <li>State vs. Committee emphasis</li>
                <li>Regional and temporal trends</li>
                <li>Five-stage cycle dynamics</li>
            </ul>
        </div>

        <div class="about-info-box" style="margin-top: 20px;">
            <h4>🔮 Future Enhancements</h4>
            <ul style="line-height: 1.8;">
                <li>World Bank Disability Data Hub integration</li>
                <li>Disability Data Initiative metrics</li>
                <li>Quantitative outcome correlations</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("💾 Data Sources")

    st.markdown("""
    **PRIMARY SOURCE:** UN Treaty Body Database
    All documents sourced from official UN communications between State Parties and the Committee.

    **FUTURE INTEGRATION:**
    - **World Bank Disability Data Hub:** Quantitative indicators on disability prevalence, outcomes
    - **Disability Data Initiative:** Complementary datasets on implementation and impact
    """)

    st.markdown("---")
    st.subheader("🛠️ Technical Stack")
    st.write("""
    - **Framework**: Streamlit + Python
    - **Visualization**: Plotly Express
    - **NLP**: scikit-learn (TF-IDF)
    - **Data Processing**: Pandas, NumPy
    - **Deployment**: Posit Connect Cloud
    """)

    st.markdown("---")
    st.subheader("👥 Research Team")

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
        Ms. Juliana Woods, American University
        Ms. Rachi Adhikari, American University
        Ms. Anja Herman, American University
        Mr. Theodore Andrew Ochieng, American University
        Ms. Mina Aydin, University of Virginia
        Ms. Ananya Chandra, McGill University
        """)

    with col2:
        st.markdown("""
        **Project Information**
        Developed: 2024-2025
        Version: 6.0
        Last Updated: December 2024

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
