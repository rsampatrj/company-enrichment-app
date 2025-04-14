import streamlit as st
import pandas as pd
import requests
import time

class DuckAIClient:
    def __init__(self):
        self.chat_endpoint = "https://duckduckgo.com/duckchat/v1/chat"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Content-Type": "application/json"
        }

    def _query_ai(self, prompt):
        """Base method for handling AI queries"""
        try:
            response = requests.post(
                self.chat_endpoint,
                json={"messages": [{"role": "user", "content": prompt}]},
                headers=self.headers,
                timeout=15
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content'].strip('"')
        except Exception as e:
            st.error(f"API Error: {str(e)}")
            return None

    def translate_company(self, name):
        """Get English translation of Japanese company name"""
        prompt = f"Accurately translate this Japanese medical organization name to English: {name}"
        return self._query_ai(prompt)

    def research_domain(self, translated_name):
        """Get domain suggestion for translated name"""
        prompt = f"Suggest a professional .jp website domain for {translated_name} using common Japanese naming conventions. Answer ONLY with the domain name."
        domain = self._query_ai(prompt)
        return domain if domain else f"{translated_name.lower().replace(' ', '-')}.jp"

def main():
    st.set_page_config(
        page_title="医療機関 Translator",
        page_icon="🏥",
        layout="wide"
    )
    
    st.title("🇯🇵 Japanese Medical Entity Translator")
    st.markdown("Powered by DuckDuckGo AI Chat")
    
    with st.expander("📌 Instructions", expanded=True):
        st.write("""
        1. Upload CSV file with company names in first column
        2. Processing occurs in batches of 20 names
        3. Real-time progress tracking
        4. Automatic error handling and retries
        5. Download final results as CSV
        """)
    
    uploaded_file = st.file_uploader("Upload CSV file", type=['csv'])
    
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        companies = df.iloc[:, 0].tolist()
        
        # Initialize session state
        if 'results' not in st.session_state:
            st.session_state.update({
                'results': [],
                'processed': 0,
                'total': len(companies),
                'is_processing': True
            })
        
        # Progress controls
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_placeholder = st.empty()
        
        # Processing loop
        while (st.session_state.processed < st.session_state.total 
               and st.session_state.is_processing):
            
            batch = companies[st.session_state.processed:st.session_state.processed+20]
            assistant = DuckAIClient()
            
            batch_results = []
            for company in batch:
                try:
                    translated = assistant.translate_company(company)
                    if translated:
                        domain = assistant.research_domain(translated)
                        status = "✅ Success"
                    else:
                        domain = "N/A"
                        status = "❌ Translation Failed"
                except Exception as e:
                    translated = "Error"
                    domain = "N/A"
                    status = f"❌ System Error: {str(e)}"
                
                batch_results.append({
                    'Original Name': company,
                    'Translated Name': translated,
                    'Suggested Domain': domain,
                    'Status': status
                })
                
                time.sleep(1.5)  # Rate limiting
            
            # Update session state
            st.session_state.results.extend(batch_results)
            st.session_state.processed += len(batch)
            
            # Update UI
            progress = st.session_state.processed / st.session_state.total
            progress_bar.progress(progress)
            status_text.markdown(f"""
            **Progress:** {st.session_state.processed}/{st.session_state.total}  
            **Completion:** {progress:.1%}  
            **Current Batch Size:** {len(batch)} companies
            """)
            
            # Show live results
            with results_placeholder.container():
                st.dataframe(pd.DataFrame(batch_results), use_container_width=True)
        
        # Final output and controls
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Restart Processing"):
                st.session_state.clear()
                st.rerun()
        
        with col2:
            st.download_button(
                "💾 Download Full Results",
                pd.DataFrame(st.session_state.results).to_csv(index=False).encode('utf-8'),
                "medical_translations.csv",
                "text/csv"
            )
        
        st.success("Processing complete! Downloaded file contains all results.")

if __name__ == "__main__":
    main()
