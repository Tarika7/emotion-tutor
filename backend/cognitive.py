import time
from logic import update_learner_history

last_time = time.time()

def edit_distance(a, b):
    dp = [[0]*(len(b)+1) for _ in range(len(a)+1)]

    for i in range(len(a)+1):
        for j in range(len(b)+1):
            if i == 0:
                dp[i][j] = j
            elif j == 0:
                dp[i][j] = i
            elif a[i-1] == b[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(
                    dp[i-1][j],
                    dp[i][j-1],
                    dp[i-1][j-1]
                )
    return dp[-1][-1]

def cognitive_score(user_answer, correct_answer, emotion="Engaged"):
    global last_time

    now = time.time()
    time_taken = now - last_time
    last_time = now

    distance = edit_distance(str(user_answer), str(correct_answer))

    score = 0
    is_correct = str(user_answer).strip() == str(correct_answer).strip()

    if is_correct:
        score += 2
    else:
        score -= 1

    if time_taken > 6:
        score -= 1
    elif time_taken < 3:
        score += 1

    if distance <= 1:
        score += 1

    # Update learner history
    update_learner_history(emotion, is_correct, time_taken)

    if score <= -1:
        return "Frustrated"
    elif score == 0:
        return "Confused"
    elif score == 1:
        return "Engaged"
    else:
        return "Bored"