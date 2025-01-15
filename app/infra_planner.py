import os
import json
from dotenv import load_dotenv
import requests
import itertools
from dataclasses import dataclass
from typing import Optional
import time


@dataclass
class Recommendation:
    status: bool
    content: str = ""
    diagram: str = ""
    error: str = ""

class InfrastructurePlanner:
    def __init__(self) -> None:
        load_dotenv()

        self.api_url = os.getenv("HUGGINGFACE_API_URL")
        self.headers = {"Authorization": f"Bearer {os.getenv('HUGGINGFACE_TOKEN')}"}

    def _create_context(self) -> str:
        """Create context from AWS services data"""
        try:
            with open('data/aws_services_data.json', 'r') as f:
                services = json.load(f)
            
            context = "AWS Services Information:\n\n"
            for service in services:
                context += f"- {service['Service Name']}: {service['Description'][:400]}...\n"
            return context
        except Exception as e:
            raise ValueError(f"Error loading AWS services data: {e}")

    def _extract_mermaid_diagram(self, text: str) -> tuple[str, str]:
        """Extract recommendation text and Mermaid diagram from response."""
        default_diagram = """```mermaid
graph TD
    Client[Client]
    subgraph AWS Cloud
        Service1[Primary Service]
    end
    Client --> Service1
```"""

        try:
            # Look for the last occurrence of ```mermaid as it should be at the end
            sections = text.split("```mermaid")
            if len(sections) < 2:
                print("No mermaid diagram found in response")
                return text.strip(), default_diagram

            # Get the last mermaid section
            content = "```mermaid".join(sections[:-1]).strip()
            diagram_section = sections[-1]

            # Find the closing backticks
            diagram_parts = diagram_section.split("```")
            if not diagram_parts:
                print("No closing backticks found")
                return text.strip(), default_diagram

            # Reconstruct the diagram with proper markers
            diagram = f"```mermaid{diagram_parts[0]}```"

            # Validate diagram content
            if not any(keyword in diagram.lower() for keyword in ['graph', 'flowchart']):
                print("Invalid diagram content - no graph definition found")
                return text.strip(), default_diagram

            if not diagram.strip():
                print("Empty diagram content")
                return text.strip(), default_diagram

            print("Successfully extracted diagram:", diagram[:100] + "...") # Debug log
            return content, diagram

        except Exception as e:
            print(f"Error in diagram extraction: {str(e)}")
            return text.strip(), default_diagram

    def generate_recommendation_and_diagram(self, user_input: str) -> Recommendation:
        """Generate both infrastructure recommendations and architecture diagram"""
        try:
            context = self._create_context()
            
            print(f"Making request to model API: {self.api_url}")
            
            prompt = f"""<s>[INST]You are an AWS Solution Architect. Create a response in TWO PARTS ONLY:

FIRST: Provide the infrastructure recommendation with these sections:

1. Requirement Analysis
- Functional Requirements (Core functionalities, business goals)
- Non-functional Requirements (Performance, security, scaling)
- Workload Characteristics (Traffic patterns, resource needs)
- Additional Considerations (Constraints, compliance)

2. Architecture Design
- Overview (Architecture summary)
- Core Services (AWS services selection and roles)
- Additional Considerations (DR, integrations)

3. Implementation Steps
- Key Steps (Setup and configuration)
- Security (IAM, encryption, networking)
- Monitoring (CloudWatch setup)
- Additional Details (CI/CD, backups)

4. Cost Optimization
- Resource Sizing (Instance types, storage)
- Pricing Models (On-Demand/Reserved/Spot)
- Optimization Strategies (Auto-scaling)
- Additional Measures (Savings plans)

SECOND: You must end your response with a complete architecture diagram in this exact format:

```mermaid
graph TD
    %% Define all AWS services as nodes
    Client[Client]
    
    %% Group related services in subgraphs
    subgraph AWS Cloud
        %% Add all relevant AWS services and their connections here
        %% Show service relationships and data flow
        %% Include security and monitoring components
    end
    
    %% Define all connections between services
    
    %% Style all AWS services
    classDef aws fill:#232F3E,stroke:#FF9900,stroke-width:2px,color:#FF9900;
    class ServiceName1,ServiceName2 aws;
```

Requirements: {user_input}

AWS Services Context:
{context}

CRITICAL INSTRUCTIONS:
1. You must include a Mermaid diagram at the end
2. The diagram must be the last part of your response
3. The diagram must start with ```mermaid and end with ```
4. Do not explain the diagram or add any text after it
5. Include all relevant AWS services in the diagram
6. Use proper AWS service names in the diagram
7. Show all connections and data flows between services
[/INST]"""
            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": 8192,
                        "return_full_text": False,
                        "temperature": 0.7,
                        "top_p": 0.95,
                    }
                },
                timeout=90
            )
            
            if response.status_code != 200:
                return Recommendation(status=False, error=f"API Error: {response.status_code}")

            try:
                generated_text = response.json()[0]['generated_text']
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                return Recommendation(status=False, error=f"Failed to parse response: {str(e)}")

            # Extract content and diagram
            content, diagram = self._extract_mermaid_diagram(generated_text)
            
            return Recommendation(
                status=True,
                content=content,
                diagram=diagram
            )
            
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return Recommendation(status=False, error=f"Unexpected error: {str(e)}")

    def create_mermaid_html(self, mermaid_code: str) -> str:
        """Create HTML with Mermaid diagram"""
        return f"""
            <div class="diagram-container" style="
                width: 100%;
                height: 800px;
                border: 1px solid #333;
                border-radius: 8px;
                position: relative;
                background: #0F1118;
                margin: 20px 0;
                display: flex;
                flex-direction: column;
            ">
                <div class="zoom-controls" style="
                    position: sticky;
                    top: 20px;
                    right: 20px;
                    z-index: 1000;
                    background: rgba(0,0,0,0.6);
                    padding: 10px;
                    border-radius: 5px;
                    margin-left: auto;
                    margin-right: 20px;
                ">
                    <button onclick="zoomIn()" style="
                        margin: 0 5px;
                        padding: 5px 10px;
                        background: #FF9900;
                        border: none;
                        border-radius: 3px;
                        color: white;
                        cursor: pointer;
                    ">+</button>
                    <button onclick="zoomOut()" style="
                        margin: 0 5px;
                        padding: 5px 10px;
                        background: #FF9900;
                        border: none;
                        border-radius: 3px;
                        color: white;
                        cursor: pointer;
                    ">-</button>
                    <button onclick="resetZoom()" style="
                        margin: 0 5px;
                        padding: 5px 10px;
                        background: #FF9900;
                        border: none;
                        border-radius: 3px;
                        color: white;
                        cursor: pointer;
                    ">Reset</button>
                </div>
                <div class="diagram-wrapper" style="
                    width: 100%;
                    flex-grow: 1;
                    overflow: auto;
                    position: relative;
                    padding: 20px;
                ">
                    <div class="mermaid" id="mermaid-diagram" style="
                        min-width: 100%;
                        transform-origin: 0 0;
                        padding-bottom: 100px;
                    ">
                        {mermaid_code}
                    </div>
                </div>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
            <script>
                let currentZoom = 1;
                const zoomFactor = 0.1;
                const diagram = document.getElementById('mermaid-diagram');

                function forceWhiteText() {{
                    const svg = document.querySelector('.mermaid svg');
                    if (svg) {{
                        // Add padding to SVG
                        svg.style.paddingBottom = '100px';
                        
                        // Add a style element to the SVG
                        const style = document.createElementNS("http://www.w3.org/2000/svg", "style");
                        style.textContent = `
                            .node text {{ fill: #FFFFFF !important; font-weight: bold !important; font-size: 16px !important; }}
                            .cluster text {{ fill: #FFFFFF !important; font-weight: bold !important; font-size: 16px !important; }}
                            .label text {{ fill: #FFFFFF !important; font-weight: bold !important; font-size: 16px !important; }}
                            .node rect {{ fill: #2C3E50 !important; stroke: #FF9900 !important; stroke-width: 2px !important; }}
                            .node circle {{ fill: #2C3E50 !important; stroke: #FF9900 !important; stroke-width: 2px !important; }}
                            .edge path {{ stroke: #FF9900 !important; stroke-width: 2px !important; }}
                            .edge text {{ fill: #FFFFFF !important; font-weight: bold !important; font-size: 14px !important; }}
                        `;
                        svg.insertBefore(style, svg.firstChild);

                        // Apply directly to elements
                        svg.querySelectorAll('text').forEach(text => {{
                            text.setAttribute('fill', '#FFFFFF');
                            text.style.fill = '#FFFFFF';
                            text.style.color = '#FFFFFF';
                        }});
                    }}
                }}
                
                function zoomIn() {{
                    currentZoom += zoomFactor;
                    updateZoom();
                }}
                
                function zoomOut() {{
                    currentZoom = Math.max(0.1, currentZoom - zoomFactor);
                    updateZoom();
                }}
                
                function resetZoom() {{
                    currentZoom = 1;
                    updateZoom();
                }}
                
                function updateZoom() {{
                    diagram.style.transform = `scale(${{currentZoom}})`;
                }}

                mermaid.initialize({{
                    startOnLoad: true,
                    theme: 'dark',
                    securityLevel: 'loose',
                    themeVariables: {{
                        primaryColor: '#FF9900',
                        primaryTextColor: '#FFFFFF',
                        primaryBorderColor: '#FF9900',
                        lineColor: '#FF9900',
                        secondaryColor: '#2C3E50',
                        tertiaryColor: '#FFFFFF'
                    }}
                }});

                document.addEventListener('DOMContentLoaded', function() {{
                    const observer = new MutationObserver((mutations, obs) => {{
                        const svg = document.querySelector('.mermaid svg');
                        if (svg) {{
                            forceWhiteText();
                            obs.disconnect();
                            
                            // Reapply on any subsequent changes
                            const svgObserver = new MutationObserver(() => forceWhiteText());
                            svgObserver.observe(svg, {{ 
                                childList: true, 
                                subtree: true,
                                attributes: true
                            }});
                        }}
                    }});

                    observer.observe(document.querySelector('.mermaid'), {{
                        childList: true,
                        subtree: true
                    }});
                }});
            </script>
        """
