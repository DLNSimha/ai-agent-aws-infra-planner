import streamlit as st
import streamlit.components.v1 as components
from infra_planner import InfrastructurePlanner
from pdf_generator import PDFGenerator
import base64
import time

def get_pdf_download_link(pdf_bytes, filename="infrastructure_plan.pdf"):
    """Generate a download link for the PDF"""
    b64 = base64.b64encode(pdf_bytes).decode()
    return f'<a href="data:application/pdf;base64,{b64}" download="{filename}" class="download-button">Download PDF</a>'

def main():
    st.set_page_config(
        page_title="AWS Infrastructure Planner",
        page_icon="⚡",
        layout="wide"
    )

    st.title("AWS Infrastructure Planner ⚡")

    # Initialize session state
    if 'planner' not in st.session_state:
        st.session_state.planner = InfrastructurePlanner()
        st.session_state.pdf_generator = PDFGenerator()
        st.session_state.current_pdf = None
        st.session_state.result = None
        st.session_state.error = None
        st.session_state.recommendation_displayed = False

    # User input
    user_input = st.text_area(
        "Describe your infrastructure requirements:",
        height=150,
        placeholder="Example: I need to build a highly available web application that can handle 1000 requests per second..."
    )

    # Add custom CSS for buttons
    st.markdown("""
        <style>
        .stButton > button {
            background-color: #FF9900;
            color: white;
            font-weight: bold;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            width: auto !important;
            white-space: nowrap;
        }
        .stButton > button:hover {
            background-color: #FF8800;
            color: white;
            border: none;
        }
        .download-button {
            background-color: #FF9900;
            color: white;
            padding: 10px 20px;
            text-decoration: none;
            border-radius: 4px;
            border: none;
            cursor: pointer;
            font-weight: bold;
            float: right;
            margin-top: 8px;
        }
        .download-button:hover {
            background-color: #FF8800;
            color: white;
            text-decoration: none;
        }
        .header-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        div.stSpinner > div {
            display: inline-flex !important;
            align-items: center;
            gap: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Generate Plan button
    generate_clicked = st.button("Generate Plan")

    if generate_clicked:
        if not user_input:
            st.warning("Please enter your requirements first.")
        else:
            with st.spinner("Generating infrastructure plan and architecture diagram..."):
                try:
                    # Generate new results
                    result = st.session_state.planner.generate_recommendation_and_diagram(user_input)
                    
                    if result.status:
                        st.session_state.result = result
                        st.session_state.recommendation_displayed = True
                        
                        # Create Mermaid HTML
                        mermaid_code = result.diagram.split("```mermaid")[-1].split("```")[0].strip()
                        mermaid_html = st.session_state.planner.create_mermaid_html(mermaid_code)
                        
                        # Generate PDF
                        try:
                            pdf_bytes = st.session_state.pdf_generator.generate_pdf(
                                result.content,
                                mermaid_code,
                                user_input
                            )
                            st.session_state.current_pdf = pdf_bytes
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to generate PDF: {str(e)}")
                    else:
                        st.error(f"Failed to generate plan: {result.error}")
                except Exception as e:
                    st.error(f"An unexpected error occurred: {str(e)}")

    # Display results if available
    if st.session_state.result and st.session_state.recommendation_displayed:
        result = st.session_state.result
        
        # Display recommendation with download button
        st.markdown("""
            <div class="header-container">
                <h2>Infrastructure Recommendation</h2>
                {}
            </div>
        """.format(get_pdf_download_link(st.session_state.current_pdf) if st.session_state.current_pdf else ""), 
        unsafe_allow_html=True)
        
        st.markdown(result.content)
        
        # Display architecture diagram
        st.markdown("## Architecture Diagram")
        mermaid_code = result.diagram.split("```mermaid")[-1].split("```")[0].strip()
        mermaid_html = st.session_state.planner.create_mermaid_html(mermaid_code)
        components.html(mermaid_html, height=600)

if __name__ == "__main__":
    main()
