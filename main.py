
import streamlit as st
import requests
from gtts import gTTS
from gtts.tts import gTTSError
from io import BytesIO
from streamlit_mic_recorder import speech_to_text
from app.llm.ollama_client import generate_response


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="LinguaBridge AI",
    page_icon="🌍",
    layout="centered"
)


# --------------------------------------------------
# LANGUAGE CONFIGURATION
# --------------------------------------------------

LANGUAGES = {
    "German": "de",
    "French": "fr",
    "Dutch": "nl"
}

TRANSLATE_URL = "https://libretranslate.com/translate"


# --------------------------------------------------
# LIBRETRANSLATE FUNCTION
# --------------------------------------------------

def translate_with_libretranslate(text, target_language, api_key=None):

    payload = {
        "q": text,
        "source": "en",
        "target": target_language,
        "format": "text"
    }

    if api_key:
        payload["api_key"] = api_key

    response = requests.post(
        TRANSLATE_URL,
        json=payload,
        timeout=30
    )

    response.raise_for_status()

    result = response.json()
    translated = result.get("translatedText", "")

    if not translated:
        raise RuntimeError(
            "LibreTranslate returned an empty response."
        )

    return translated


# --------------------------------------------------
# OLLAMA TRANSLATION FUNCTION
# --------------------------------------------------

def translate_with_ollama(text, language):

    prompt = f"""
You are a professional translator.

Translate the following English text into {language}.

Rules:
- Translate only. Do not answer the text.
- Preserve the original meaning and tone.
- Do not explain anything.
- Do not add introductions or comments.
- Return only the translated text.

English text:
{text}

{language} translation:
"""

    translated = generate_response(prompt).strip()

    if translated.startswith("Error:") or translated.startswith(
        "Ollama API error:"
    ):
        raise RuntimeError(translated)

    if not translated:
        raise RuntimeError(
            "Ollama returned an empty response."
        )

    return translated


# --------------------------------------------------
# TEXT-TO-SPEECH FUNCTION
# --------------------------------------------------

def generate_speech(text, language_code):

    audio_buffer = BytesIO()

    speech = gTTS(
        text=text,
        lang=language_code,
        slow=False
    )

    speech.write_to_fp(audio_buffer)
    audio_buffer.seek(0)

    return audio_buffer.getvalue()


# --------------------------------------------------
# MAIN APPLICATION UI
# --------------------------------------------------

st.title("🌍 LinguaBridge AI")

st.subheader("Your Personal Multilingual AI Assistant")

st.write(
    "Translate sentences and listen to their pronunciation "
    "using AI-powered tools."
)

st.divider()


# --------------------------------------------------
# SIDEBAR SETTINGS
# --------------------------------------------------

with st.sidebar:

    st.header("Settings")

    provider = st.selectbox(
        "Choose translation provider",
        ["Ollama (Local AI)", "LibreTranslate"]
    )

    st.write("Available languages:")

    for language_name in LANGUAGES:
        st.write(f"- {language_name}")

    api_key = ""

    if provider == "LibreTranslate":

        api_key = st.text_input(
            "LibreTranslate API Key",
            type="password"
        )

    st.caption(
        "Ollama runs locally. Voice input uses Google's "
        "speech recognition service. Voice generation "
        "through gTTS requires an internet connection."
    )


# --------------------------------------------------
# TARGET LANGUAGE SELECTION
# --------------------------------------------------

language = st.selectbox(
    "Select your target language",
    list(LANGUAGES.keys())
)

target_code = LANGUAGES[language]


# --------------------------------------------------
# VOICE INPUT / SPEECH-TO-TEXT
# --------------------------------------------------

st.divider()

st.subheader("🎤 Voice Input")

st.write(
    "Click the microphone button and speak in English."
)

if "english_input" not in st.session_state:
    st.session_state["english_input"] = ""

spoken_text = speech_to_text(
    language="en",
    start_prompt="🎤 Start speaking",
    stop_prompt="⏹️ Stop recording",
    just_once=True,
    use_container_width=True,
    key="english_voice_input"
)

if spoken_text:
    st.session_state["english_input"] = spoken_text


# --------------------------------------------------
# ENGLISH TEXT INPUT
# --------------------------------------------------

english_text = st.text_area(
    "Enter your English sentence",
    key="english_input",
    placeholder="Good morning. How are you?",
    height=130
)


# --------------------------------------------------
# TRANSLATION BUTTON
# --------------------------------------------------

if st.button(
    "Translate",
    type="primary",
    use_container_width=True
):

    if not english_text.strip():

        st.warning("Please enter or speak an English sentence.")

    else:

        try:

            with st.spinner("Translating..."):

                if provider == "Ollama (Local AI)":

                    translated_text = translate_with_ollama(
                        english_text.strip(),
                        language
                    )

                else:

                    translated_text = translate_with_libretranslate(
                        english_text.strip(),
                        target_code,
                        api_key.strip() if api_key else None
                    )

            st.session_state["translated_text"] = translated_text

            st.session_state["original_text"] = english_text.strip()

            st.session_state["target_code"] = target_code

            st.session_state["target_language"] = language

            # Clear old audio when a new translation is generated
            st.session_state.pop("audio_data", None)

            st.success("Translation completed successfully!")

        except requests.exceptions.Timeout:

            st.error("Translation timed out. Please try again.")

        except requests.exceptions.ConnectionError:

            st.error("Could not connect to the translation service.")

        except requests.exceptions.HTTPError as error:

            st.error(f"Translation server returned an HTTP error: {error}")

        except requests.exceptions.RequestException as error:

            st.error(f"Network error: {error}")

        except RuntimeError as error:

            st.error(f"Translation error: {error}")


# --------------------------------------------------
# DISPLAY TRANSLATION
# --------------------------------------------------

if "translated_text" in st.session_state:

    st.divider()

    st.subheader(
        f"{st.session_state['target_language']} Translation"
    )

    st.success(st.session_state["translated_text"])

    st.subheader("Original English")

    st.info(st.session_state["original_text"])


    # --------------------------------------------------
    # VOICE GENERATION
    # --------------------------------------------------

    st.divider()

    st.subheader("🔊 Voice Pronunciation")

    if st.button(
        "Generate Voice",
        use_container_width=True
    ):

        try:

            with st.spinner("Generating speech..."):

                audio_data = generate_speech(
                    st.session_state["translated_text"],
                    st.session_state["target_code"]
                )

                st.session_state["audio_data"] = audio_data

            st.success("Voice generated successfully!")

        except gTTSError as error:

            st.error(f"Text-to-speech error: {error}")

        except requests.exceptions.Timeout:

            st.error("Voice generation timed out. Please try again.")

        except requests.exceptions.ConnectionError:

            st.error("Could not connect to the voice service.")

        except requests.exceptions.RequestException as error:

            st.error(f"Voice generation network error: {error}")


    # --------------------------------------------------
    # AUDIO PLAYBACK AND REPLAY
    # --------------------------------------------------

    if "audio_data" in st.session_state:

        st.subheader("🎧 Listen to Your Translation")

        st.audio(
            st.session_state["audio_data"],
            format="audio/mp3"
        )

        st.caption(
            "Use the audio player's play button to replay the voice."
        )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption("LinguaBridge AI | Version 1.2")
