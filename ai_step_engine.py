def generate_better_step(current_step):

    print("🔥 FUNCTION ENTERED")   # ADD THIS

    if not current_step:
        return current_step

    print("🔥 AI CALLED FOR STEP:", current_step)

    try:
        print("🔥 BEFORE API CALL")   # ADD THIS

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": f"Improve this execution step:\n{current_step}"
                }
            ],
            temperature=0.7
        )

        print("🔥 AFTER API CALL")   # ADD THIS

        improved = response.choices[0].message.content.strip()

        print("🔥 AI RESPONSE:", improved)

        return improved if improved else current_step

    except Exception as e:
        print("🚨 AI ERROR:", str(e))
        return f"Improve execution of: {current_step}"