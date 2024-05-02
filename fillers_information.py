import random

# List of filler sentences
filler_sentences = [
    "Just a sec while I look that up.",
    "Hold on, I am getting that for you.",
    "Just One moment, please.",
    "Just checking that for you.",
    "Give me just a moment.",
    "Almost got it, one sec.",
    "Just a sec, let me check."
]

Question_filler_sentences = [
    "Just a moment, please.", "Hold on a sec while I handle that.",
    "I'm getting that sorted, please bear with me.",
    "Bear with me as I pull that up for you."
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
