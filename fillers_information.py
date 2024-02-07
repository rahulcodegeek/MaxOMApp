import random

# List of filler sentences
filler_sentences = [
    "Hmmm, give me a second...",
    "Just a moment...",
    "Hang on, Just a moment...",
    "Give me a moment while i check...",
    "Bear with me for a moment while i process this information.",
    "Hmmm... Let me see... Appreciate your patience.",
    "Please wait for a moment, while i process this information."
]

Question_filler_sentences = [
    "Please wait for a moment while I consider your question.",
    "Bear with me for a moment while i process this information.",
    "Thats an interesting question.",
    "Python is a versatile programming language.",
    "Let me check."
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
