import random

# List of filler sentences
filler_sentences = [
    "Sure, please give me a second here ...... as I pull up the necessary details for you",
    "Just a moment, I'm quickly verifying the information to assist you better",
    "Please hold for a moment, I'm just checking that for you",
    "Hmm...... Let me see here...... Please wait for a moment as I review this for you",
]

Question_filler_sentences = [
    "Please wait for a moment......, while I process this information for you",
    "Bear with me for a moment...... while I gather some information to address your query"
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
