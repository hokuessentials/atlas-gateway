from openai import OpenAI
import os

client = OpenAI()

def generate_better_step(current_step):

    print("🔥 FUNCTION ENTERED")

    if not current_step:
        return current_step

    try:
        print("🔥 BEFORE API CALL")

        response = client.responses.create(
            model="gpt-4o-mini",
            input=f"Improve this execution step:\n{current_step}"
        )

        print("🔥 AFTER API CALL")

        if response.output and len(response.output) > 0:
            content = response.output[0].content

            if content and len(content) > 0 and hasattr(content[0], "text"):
                improved = content[0].text.strip()
            else:
                improved = current_step
        else:
            improved = current_step

        print("🔥 AI RESPONSE:", improved)

        return improved

    except Exception as e:
        print("🚨 AI ERROR:", str(e))
        return f"Improve execution of: {current_step}"