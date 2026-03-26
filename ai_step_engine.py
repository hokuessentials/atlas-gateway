import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_better_step(current_step):

    if not current_step:
        return current_step

    print("AI CALLED FOR STEP:", current_step)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": f"Improve this execution step to make it more specific and effective:\n{current_step}"
                }
            ],
            temperature=0.7
        )

        improved = response.choices[0].message.content.strip()

        print("AI RESPONSE:", improved)

        return improved if improved else current_step

    except Exception as e:
        print("🚨 AI ERROR:", str(e))
        return f"Improve execution of: {current_step}"