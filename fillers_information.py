import random

# List of filler sentences
filler_sentences = [
    "Gathering details, one moment.",
    "Retrieving details momentarily, standby.",
    "Verifying, one moment please.",
    "Verifying information, please wait for a moment.",
    "Checking, please hold for updates.",
    "Hmm...Reviewing briefly, just a moment.",
    "Reviewing, please wait briefly."
]

Question_filler_sentences = [
    "Processing, please wait just a moment.",
    "Processing, please wait a moment.",
    "Gathering information, please bear with me.",
    "Bear with me as I gather information for you."
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
