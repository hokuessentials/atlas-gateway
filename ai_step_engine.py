from openai import OpenAI
import os

client = OpenAI()

def generate_better_step(current_step):

    print("🔥 FUNCTION ENTERED")

    if not current_step:
        return current_step

    print("🔥 AI CALLED FOR STEP:", current_step)

    try:
        print("🔥 BEFORE API CALL")

        response = client.responses.create(
            model="gpt-4o-mini",
            input=f"Improve this execution step:\n{current_step}"
        )

        print("🔥 AFTER API CALL")

        improved = response.output[0].content[0].text.strip()

        print("🔥 AI RESPONSE:", improved)

        return improved if improved else current_step

    except Exception as e:
        print("🚨 AI ERROR:", str(e))
        return f"Improve execution of: {current_step}"