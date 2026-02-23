import streamlit as st
import speech_recognition as sr
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from textblob import TextBlob
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Download NLTK data if needed
nltk.download('vader_lexicon', quiet=True)
nltk.download('punkt', quiet=True)

def get_transcript():
    """Function to get transcript either by pasting or dictating."""
    input_method = st.radio("Input Method:", ("Paste Text", "Dictate"))
    
    if input_method == "Paste Text":
        transcript = st.text_area("Paste your meeting transcript here:", height=300)
    else:
        st.info("Click the button below and speak into your microphone. Say 'stop' to end dictation.")
        if st.button("Start Dictation"):
            recognizer = sr.Recognizer()
            transcript = ""
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source)
                st.write("Listening... Say 'stop' to end.")
                while True:
                    try:
                        audio = recognizer.listen(source, timeout=5)
                        text = recognizer.recognize_google(audio)
                        if "stop" in text.lower():
                            break
                        transcript += text + " "
                        st.write("Transcribed so far: " + transcript)
                    except sr.WaitTimeoutError:
                        continue
                    except sr.UnknownValueError:
                        st.warning("Could not understand audio. Try again.")
            st.text_area("Dictated Transcript (editable):", value=transcript, height=300)
    
    return transcript

def summarize_transcript(transcript):
    """Summarize the transcript using Sumy LSA."""
    if not transcript:
        return ""
    parser = PlaintextParser.from_string(transcript, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, 5)  # 5 sentences summary
    return " ".join(str(sentence) for sentence in summary)

def extract_action_items(transcript):
    """Extract action items using simple regex patterns."""
    action_patterns = [
        r"(?i)\b(action|todo|task|assign|do|follow up|next step)\b.*?(?=\.)",
        r"(?i)\b(\w+)(?: needs to| will| should| must)\b\s*(.*?)(?=\.)"
    ]
    actions = []
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', transcript)
    for sentence in sentences:
        for pattern in action_patterns:
            match = re.search(pattern, sentence)
            if match:
                actions.append(sentence.strip())
    return list(set(actions))  # Remove duplicates

def analyze_sentiment(transcript):
    """Analyze sentiment using VADER."""
    sia = SentimentIntensityAnalyzer()
    scores = sia.polarity_scores(transcript)
    compound = scores['compound']
    if compound >= 0.05:
        return "Positive"
    elif compound <= -0.05:
        return "Negative"
    else:
        return "Neutral"

def generate_report(transcript):
    """Generate formatted report."""
    summary = summarize_transcript(transcript)
    actions = extract_action_items(transcript)
    sentiment = analyze_sentiment(transcript)
    
    report = f"""
# Meeting Notes Report

## Key Points Summary
{summary}

## Action Items
"""
    if actions:
        for i, action in enumerate(actions, 1):
            report += f"{i}. {action}\n"
    else:
        report += "No action items detected.\n"
    
    report += f"""
## Overall Sentiment
{sentiment}

## Full Transcript
{transcript}
"""
    return report

def send_email(report, sender_email, sender_password, recipient_email):
    """Send the report via email using SMTP."""
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = "Meeting Notes Report"
    msg.attach(MIMEText(report, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Error sending email: {str(e)}")
        return False

# Streamlit App
st.title("Meeting Notes AI Condenser")

transcript = get_transcript()

if st.button("Generate Report") and transcript:
    with st.spinner("Processing..."):
        report = generate_report(transcript)
        st.markdown(report)
        
        # Optional Email Send
        st.subheader("Send Report via Email")
        sender_email = st.text_input("Your Email (Gmail):")
        sender_password = st.text_input("Your Email Password:", type="password")
        recipient_email = st.text_input("Recipient Email:")
        
        if st.button("Send Email") and sender_email and sender_password and recipient_email:
            if send_email(report, sender_email, sender_password, recipient_email):
                st.success("Report sent successfully!")
