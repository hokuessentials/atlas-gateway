from openai import OpenAI
import os

# Initialize client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_better_step(current_step):

    # ✅ GUARD 1: Empty or too long
    if not current_step or len(current_step) > 300:
        print("⚠️ SKIPPING AI CALL (invalid or too long)")
        return current_step

    # ✅ GUARD 2: Prevent infinite improvement loop
    if "improve execution of" in current_step.lower():
        print("⚠️ SKIPPING AI CALL (loop detected)")
        return current_step

    try:
        print("🔥 BEFORE API CALL")

        response = client.responses.create(
            model="gpt-4o-mini",
            input=f"""
You are an execution optimizer.

Rewrite the following step into ONE clear, short, actionable step.

Rules:
- Output ONLY one sentence
- No explanation
- No multiple options
- No bullet points

Step:
{current_step}
"""
        )

        print("🔥 AFTER API CALL")

        # ✅ Extract response safely
        if hasattr(response, "output_text") and response.output_text:
            output = response.output_text.strip()
        else:
            try:
                output = response.output[0].content[0].text.strip()
            except:
                return current_step

        # ✅ CLEAN OUTPUT (VERY IMPORTANT)
        output = output.split(".")[0] + "."

        return output

    except Exception as e:
        print("🚨 AI ERROR:", str(e))

        # ✅ FAIL SAFE (never break system)
        return current_step