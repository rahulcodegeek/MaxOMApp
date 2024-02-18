import random

# List of filler sentences
filler_sentences = [
    "Certainly, just a moment while I gather the necessary details for you.",
    "Certainly, let me quickly retrieve the details for you.",
    "One moment, verifying information to assist you better.",
    "I'm verifying the information to assist you; just a moment.",
    "Please hold, I'm checking that for you.",
    "Hmm...Let me review this briefly for you.",
    "Please wait while I review this for you."
]

Question_filler_sentences = [
    "Please wait a moment as I process this information for you.",
    "Please wait as I process this information.",
    "Bear with me a moment as I gather information for you.",
    "Bear with me as I gather information for your query."
]

# List to keep track of selected sentences
selected_sentences = []
# List to keep track of selected sentences
question_selected_sentences = []


def get_randomly_filler_sentence():
    # If all sentences have been used, reset the list
    if len(selected_sentences) == len(filler_sentences):
        selected_sentences.clear()
    # Get a random sentence that hasn't been selected before
    sentence = random.choice([sentence for sentence in filler_sentences if sentence not in selected_sentences])
    selected_sentences.append(sentence)
    return sentence


def get_randomly_question_filler_sentence():
    # If all sentences have been used, reset the list
    if len(question_selected_sentences) == len(Question_filler_sentences):
        question_selected_sentences.clear()
    # Get a random sentence that hasn't been selected before
    sentence = random.choice([sentence for sentence in Question_filler_sentences if sentence not in question_selected_sentences])
    question_selected_sentences.append(sentence)
    return sentence
