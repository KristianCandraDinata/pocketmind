from google import genai

c = genai.Client()
print("Model flash yang tersedia:")
for m in c.models.list():
    if "flash" in m.name:
        print(" ", m.name)

r = c.models.generate_content(model="gemini-3.6-flash",
                              contents="Katakan halo dalam satu kalimat.")
print("Balasan:", r.text)