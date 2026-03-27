from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_better_step(current_step):

    # ✅ STEP 1: SIMPLE GUARD (ADD HERE)
    if not current_step or len(current_step) > 300:
        print("⚠️ SKIPPING AI CALL (invalid or too long)")
        return current_step

    try:
        print("🔥 BEFORE API CALL")

        response = client.responses.create(
            model="gpt-4o-mini",
            input=f"Improve this execution step:\n{current_step}"
        )

        print("🔥 AFTER API CALL")

        # ✅ SAFE RESPONSE EXTRACTION
        if hasattr(response, "output_text") and response.output_text:
            return response.output_text.strip()

        try:
            return response.output[0].content[0].text.strip()
        except:
            return current_step

    except Exception as e:
        print("🚨 AI ERROR:", str(e))

        # ✅ FAIL SAFE
        return current_step