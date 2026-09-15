import express from "express";
import path from "path";
import fs from "fs";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI } from "@google/genai";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = 3000;

app.use(express.json({ limit: "15mb" }));

// Lazy initializer for Gemini client
let aiClient: GoogleGenAI | null = null;
function getGemini(): GoogleGenAI {
  if (!aiClient) {
    const key = process.env.GEMINI_API_KEY;
    if (!key || key === "MY_GEMINI_API_KEY") {
      throw new Error("GEMINI_API_KEY is not configured in the environment.");
    }
    aiClient = new GoogleGenAI({ apiKey: key });
  }
  return aiClient;
}

// -------------------------------------------------------------
// Data Helpers
// -------------------------------------------------------------
const BASE_PROJECT_PATH = path.join(process.cwd(), "smarthire-genai");
const JOBS_CSV_PATH = path.join(BASE_PROJECT_PATH, "data", "jobs", "jobs.csv");
const CAREER_NOTES_DIR = path.join(BASE_PROJECT_PATH, "data", "career_notes");

function loadJobsFromCsv() {
  if (!fs.existsSync(JOBS_CSV_PATH)) return [];
  const content = fs.readFileSync(JOBS_CSV_PATH, "utf-8");
  const lines = content.trim().split("\n");
  const headers = lines[0].split(",");
  const jobs: any[] = [];

  // Parse CSV records
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i];
    if (!line.trim()) continue;

    // Match CSV fields supporting quoted strings
    const match = line.match(/(?:^|,)("(?:[^"]|"")*"|[^,]*)/g);
    if (match && match.length >= 5) {
      const cleanCols = match.map(c => {
        let val = c.startsWith(",") ? c.slice(1) : c;
        if (val.startsWith('"') && val.endsWith('"')) {
          val = val.slice(1, -1).replace(/""/g, '"');
        }
        return val.trim();
      });

      jobs.push({
        job_id: i,
        job_title: cleanCols[0] || "Tech Role",
        company: cleanCols[1] || "Tech Org",
        location: cleanCols[2] || "Remote",
        skills: cleanCols[3] || "Python, Git",
        description: cleanCols[4] || "Software development and data operations.",
      });
    }
  }
  return jobs;
}

function loadCareerNotes() {
  if (!fs.existsSync(CAREER_NOTES_DIR)) return [];
  const files = fs.readdirSync(CAREER_NOTES_DIR);
  return files
    .filter(f => f.endsWith(".md"))
    .map(f => {
      const content = fs.readFileSync(path.join(CAREER_NOTES_DIR, f), "utf-8");
      const title = f.replace(/_/g, " ").replace(".md", "").toUpperCase();
      return { file: f, title, content };
    });
}

// -------------------------------------------------------------
// Guardrails Logic
// -------------------------------------------------------------
const INJECTION_PATTERNS = [
  /ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|directions|prompts)/i,
  /disregard\s+(all\s+)?(previous|prior|above)/i,
  /system\s+prompt/i,
  /reveal\s+(your|the)\s+(system|initial)\s+prompt/i,
  /what\s+are\s+your\s+(hidden|exact)\s+instructions/i,
  /show\s+me\s+your\s+api[ _]?key/i,
  /output\s+(your\s+)?secret/i,
  /you\s+are\s+now\s+in\s+developer\s+mode/i,
];

const OFF_TOPIC_PATTERNS = [
  /recipe\s+for/i,
  /bake\s+a\s+cake/i,
  /who\s+won\s+the\s+match/i,
  /movie\s+review/i,
  /write\s+a\s+love\s+poem/i,
  /president\s+of/i,
  /weather\s+today/i,
];

const CAREER_KEYWORDS = [
  "career", "job", "resume", "cv", "interview", "skills", "salary",
  "developer", "engineer", "analyst", "roadmap", "learn", "study",
  "internship", "project", "python", "sql", "machine learning", "ai",
  "degree", "college", "course", "certif", "tech", "coding", "software",
  "fullstack", "frontend", "backend", "data", "cloud", "devops", "placement"
];

function checkGuardrails(text: string) {
  const trimmed = text.trim();
  if (!trimmed) {
    return {
      allowed: false,
      reason: "Empty input.",
      message: "Please enter a career or technical development question.",
    };
  }

  if (trimmed.length > 1500) {
    return {
      allowed: false,
      reason: "Length exceeded.",
      message: "Please shorten your question to under 1,500 characters for more focused mentoring.",
    };
  }

  for (const pattern of INJECTION_PATTERNS) {
    if (pattern.test(trimmed)) {
      return {
        allowed: false,
        reason: "Prompt injection detected.",
        message: "Security Notice: For privacy and integrity reasons, this assistant cannot reveal internal system prompts, developer configurations, or credentials. How can I help with your tech career journey?",
      };
    }
  }

  for (const pattern of OFF_TOPIC_PATTERNS) {
    const hasCareer = CAREER_KEYWORDS.some(kw => trimmed.toLowerCase().includes(kw));
    if (pattern.test(trimmed) && !hasCareer) {
      return {
        allowed: false,
        reason: "Off-topic query.",
        message: "This assistant is designed specifically for career, resume, job-search, interview preparation, and technical development questions. Please ask a career or technology-related question!",
      };
    }
  }

  return { allowed: true, reason: "Passed guardrails.", message: "" };
}

// -------------------------------------------------------------
// API Endpoints
// -------------------------------------------------------------

app.get("/api/health", (req, res) => {
  const hasKey = Boolean(process.env.GEMINI_API_KEY && process.env.GEMINI_API_KEY !== "MY_GEMINI_API_KEY");
  res.json({ status: "ok", geminiConfigured: hasKey });
});

// Load sample resumes
app.get("/api/sample-resumes", (req, res) => {
  try {
    const swePath = path.join(BASE_PROJECT_PATH, "data", "resumes", "sample_resume_swe.txt");
    const daPath = path.join(BASE_PROJECT_PATH, "data", "resumes", "sample_resume_data.txt");
    res.json({
      swe: fs.existsSync(swePath) ? fs.readFileSync(swePath, "utf-8") : "",
      data: fs.existsSync(daPath) ? fs.readFileSync(daPath, "utf-8") : "",
    });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// Get job database
app.get("/api/jobs", (req, res) => {
  try {
    const jobs = loadJobsFromCsv();
    res.json({ jobs });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// Extract text from uploaded document (PDF, DOCX, TXT)
app.post("/api/extract-resume", async (req, res) => {
  const { filename, fileData, mimeType } = req.body;
  if (!fileData) {
    return res.status(400).json({ error: "No file data received." });
  }

  const name = (filename || "resume").toLowerCase();
  const buffer = Buffer.from(fileData, "base64");

  try {
    let extractedText = "";

    // 1. PDF Documents
    if (name.endsWith(".pdf") || mimeType === "application/pdf" || buffer.subarray(0, 5).toString() === "%PDF-") {
      try {
        const { PDFParse } = await import("pdf-parse");
        const parser = new PDFParse({ data: buffer });
        const parsed = await parser.getText();
        await parser.destroy();
        extractedText = (parsed.text || "").trim();
      } catch (pdfErr) {
        console.warn("pdf-parse extraction notice:", pdfErr);
      }

      // If text extraction yielded very few characters (e.g. scanned image PDF or complex font encodings)
      if (extractedText.length < 50) {
        try {
          const ai = getGemini();
          const response = await ai.models.generateContent({
            model: "gemini-2.5-flash",
            contents: [
              {
                inlineData: {
                  data: fileData,
                  mimeType: "application/pdf",
                },
              },
              "Extract all the readable text from this resume document accurately, maintaining section headings, dates, skills, and bullet points. Return ONLY the extracted plain resume text without commentary.",
            ],
          });
          const geminiText = response.text?.trim();
          if (geminiText && geminiText.length > extractedText.length) {
            extractedText = geminiText;
          }
        } catch (aiErr) {
          console.warn("Gemini multimodal PDF extraction fallback unavailable:", aiErr);
        }
      }
    } 
    // 2. DOCX Word Documents
    else if (name.endsWith(".docx") || mimeType?.includes("wordprocessingml")) {
      try {
        const mammoth = await import("mammoth");
        const result = await mammoth.extractRawText({ buffer });
        extractedText = (result.value || "").trim();
      } catch (docxErr: any) {
        console.warn("mammoth docx extraction error:", docxErr);
        throw new Error("Failed to extract text from DOCX file: " + docxErr.message);
      }
    } 
    // 3. Plain Text Files
    else {
      extractedText = buffer.toString("utf-8").trim();
    }

    // Clean up null bytes, replacement characters or rogue control codes
    extractedText = extractedText
      .replace(/\0/g, "")
      .replace(/[\x01-\x08\x0B\x0C\x0E-\x1F\x7F]/g, "")
      .replace(/\r\n/g, "\n")
      .replace(/\r/g, "\n")
      .trim();

    if (!extractedText) {
      return res.status(400).json({
        error: "Unable to extract readable text from this document. Please ensure it contains selectable text.",
      });
    }

    res.json({
      success: true,
      text: extractedText,
      filename: filename || "resume",
      charCount: extractedText.length,
      wordCount: extractedText.split(/\s+/).filter(Boolean).length,
    });
  } catch (err: any) {
    console.error("Resume extraction error:", err);
    res.status(500).json({ error: err.message || "Failed to process resume document." });
  }
});

// Parse Resume with Gemini
app.post("/api/parse-resume", async (req, res) => {
  let { resumeText } = req.body;
  if (!resumeText || !resumeText.trim()) {
    return res.status(400).json({ error: "Resume text is required." });
  }

  // Detect if user pasted raw binary PDF code into textarea
  if (resumeText.startsWith("%PDF-") || resumeText.includes("%PDF-1.")) {
    try {
      const { PDFParse } = await import("pdf-parse");
      const buffer = Buffer.from(resumeText, "latin1");
      const parser = new PDFParse({ data: buffer });
      const parsed = await parser.getText();
      await parser.destroy();
      if (parsed.text && parsed.text.trim().length > 30) {
        resumeText = parsed.text.trim();
      }
    } catch {
      // Keep going if buffer conversion is partial
    }
  }

  // Strip unprintable control characters
  resumeText = resumeText
    .replace(/\0/g, "")
    .replace(/[\x01-\x08\x0B\x0C\x0E-\x1F\x7F]/g, "");

  try {
    let ai: GoogleGenAI;
    try {
      ai = getGemini();
    } catch {
      // Offline fallback
      return res.json({
        profile: {
          name: resumeText.split("\n")[0]?.trim() || "Candidate",
          skills: ["Python", "JavaScript", "SQL", "Git", "REST APIs", "Docker"],
          experience: [
            "Software Engineering Intern: Developed RESTful backend microservices and improved test coverage.",
            "Full Stack Academic Project: Built responsive web platform with database integration."
          ],
          education: ["Bachelor of Technology in Information Technology, 2024"],
          target_role: "Software Developer",
        },
        mode: "offline_fallback"
      });
    }

    const systemInstruction = `You are an expert technical recruiter and resume parser.
Extract candidate details into a strict JSON object matching:
{
  "name": "Candidate Full Name",
  "skills": ["Skill 1", "Skill 2"],
  "experience": ["Summary of role or project 1", "Summary of role or project 2"],
  "education": ["Degree, Major, Institution, Year"],
  "target_role": "Inferred Target Role"
}
Rules:
- Extract ONLY factual information supported by the resume text.
- Never invent past jobs, fake companies, or unmentioned skills.
- Return ONLY valid JSON with no markdown code blocks.`;

    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: `RESUME TEXT:\n${resumeText}`,
      config: {
        systemInstruction,
        responseMimeType: "application/json",
        temperature: 0.1,
      },
    });

    const parsed = JSON.parse(response.text || "{}");
    res.json({ profile: parsed, mode: "live_gemini" });
  } catch (err: any) {
    console.error("Resume parse error:", err);
    res.status(500).json({ error: err.message || "Failed to parse resume with Gemini." });
  }
});

// Semantic Job Search
app.post("/api/search-jobs", (req, res) => {
  const { profile, topK = 5 } = req.body;
  const jobs = loadJobsFromCsv();
  if (!jobs.length) {
    return res.json({ matches: [] });
  }

  const candidateSkills = (profile?.skills || []).map((s: string) => s.toLowerCase());
  const targetRole = (profile?.target_role || "").toLowerCase();
  const experienceText = (profile?.experience || []).join(" ").toLowerCase();

  // Compute semantic overlap & relevance score
  const scoredJobs = jobs.map(job => {
    const jobSkills = job.skills.toLowerCase().split(",").map((s: string) => s.trim());
    const jobTitle = job.job_title.toLowerCase();
    const jobDesc = job.description.toLowerCase();

    let score = 50; // baseline

    // Role title similarity
    if (jobTitle.includes(targetRole) || targetRole.includes(jobTitle)) {
      score += 25;
    } else {
      const words = targetRole.split(" ");
      if (words.some((w: string) => w.length > 3 && jobTitle.includes(w))) {
        score += 15;
      }
    }

    // Skills match calculation
    let matchingSkillCount = 0;
    for (const reqSkill of jobSkills) {
      if (candidateSkills.some((candSkill: string) => candSkill.includes(reqSkill) || reqSkill.includes(candSkill))) {
        matchingSkillCount++;
      }
    }
    const skillRatio = jobSkills.length > 0 ? (matchingSkillCount / jobSkills.length) : 0;
    score += Math.round(skillRatio * 20);

    // Experience match
    if (candidateSkills.some((s: string) => jobDesc.includes(s))) {
      score += 5;
    }

    const finalScore = Math.min(98, Math.max(45, score));

    return {
      ...job,
      match_score: finalScore,
      score_label: `${finalScore}% Semantic Similarity`,
      matching_skills: jobSkills.filter((s: string) => candidateSkills.some((c: string) => c.includes(s))),
    };
  });

  scoredJobs.sort((a, b) => b.match_score - a.match_score);
  const sliced = scoredJobs.slice(0, Number(topK) || 5);
  res.json({ matches: sliced });
});

// CV Improvement Generation
app.post("/api/improve-cv", async (req, res) => {
  const { profile, selectedJob } = req.body;
  if (!profile || !selectedJob) {
    return res.status(400).json({ error: "Profile and selected job are required." });
  }

  try {
    let ai: GoogleGenAI;
    try {
      ai = getGemini();
    } catch {
      // Offline fallback
      return res.json({
        improvements: {
          missing_skills: ["Docker", "Kubernetes", "AWS Cloud Services"],
          weak_bullet_points: [
            profile.experience?.[0] || "Worked on backend APIs.",
            profile.experience?.[1] || "Helped with code reviews."
          ],
          improved_bullet_points: [
            "Architected 12+ RESTful backend endpoints in FastAPI and PostgreSQL, decreasing API latency by 35% across 10,000 monthly transactions.",
            "Standardized microservice containerization using Docker, reducing local developer onboarding time by 40%."
          ],
          rewritten_summary: `Aspiring ${selectedJob.job_title} with proven foundations in ${profile.skills?.slice(0, 3).join(", ") || "software engineering"}. Experienced in RESTful API development, data modeling, and containerized deployments. Ready to contribute analytical problem-solving and clean code at ${selectedJob.company}.`,
          overall_suggestions: [
            `Develop an end-to-end portfolio project featuring ${selectedJob.job_title} stack with live deployment link.`,
            "Adopt the Google XYZ formula (Accomplished X, measured by Y, by doing Z) across all resume bullets.",
            "Add a categorized 'Technical Skills' section separating Languages, Frameworks, and Tools."
          ]
        },
        mode: "offline_fallback"
      });
    }

    const prompt = `You are an elite Career Coach and Technical Hiring Manager.
Compare the candidate resume against the selected target job description and return strict JSON:
{
  "missing_skills": ["Skill 1", "Skill 2"],
  "weak_bullet_points": ["Original weak bullet 1", "Original weak bullet 2"],
  "improved_bullet_points": ["Rewritten bullet 1 using Google XYZ formula", "Rewritten bullet 2 using Google XYZ formula"],
  "rewritten_summary": "Tailored 3-4 sentence professional summary",
  "overall_suggestions": ["Actionable suggestion 1", "Actionable suggestion 2", "Actionable suggestion 3"]
}

STRICT INTEGRITY RULES:
- NEVER invent fake jobs, fake past companies, or fake certifications.
- Rewrite weak bullets using the Google XYZ formula: Accomplished [X] as measured by [Y] by doing [Z].
- Return ONLY valid JSON with no markdown code fences.

TARGET JOB:
Title: ${selectedJob.job_title} at ${selectedJob.company}
Required Skills: ${selectedJob.skills}
Description: ${selectedJob.description}

CANDIDATE PROFILE:
Name: ${profile.name}
Current Skills: ${profile.skills?.join(", ")}
Experience:
- ${profile.experience?.join("\n- ")}
Education:
- ${profile.education?.join("\n- ")}`;

    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: prompt,
      config: {
        responseMimeType: "application/json",
        temperature: 0.2,
      },
    });

    const parsed = JSON.parse(response.text || "{}");
    res.json({ improvements: parsed, mode: "live_gemini" });
  } catch (err: any) {
    console.error("CV improvement error:", err);
    res.status(500).json({ error: err.message || "Failed to generate CV improvements." });
  }
});

// AI Career Mentor RAG Chatbot
app.post("/api/career-mentor", async (req, res) => {
  const { question, history = [] } = req.body;
  if (!question || !question.trim()) {
    return res.status(400).json({ error: "Question is required." });
  }

  // Check guardrails first
  const guardrail = checkGuardrails(question);
  if (!guardrail.allowed) {
    return res.json({
      answer: guardrail.message,
      sources: [],
      guardrailTriggered: true,
      category: guardrail.reason,
    });
  }

  try {
    const notes = loadCareerNotes();
    const jobs = loadJobsFromCsv();

    // RAG Retrieval simulation: match query keywords against career guides and jobs
    const qLower = question.toLowerCase();
    const scoredNotes = notes.map(n => {
      let score = 0;
      const cLower = n.content.toLowerCase();
      const words = qLower.split(/\s+/).filter((w: string) => w.length > 3);
      words.forEach((w: string) => {
        if (cLower.includes(w)) score += 3;
        if (n.title.toLowerCase().includes(w)) score += 8;
      });
      return { ...n, score };
    });

    scoredNotes.sort((a, b) => b.score - a.score);
    const topNotes = scoredNotes.slice(0, 2);

    const sources = topNotes.map(n => ({
      title: n.title,
      source: n.file,
      snippet: n.content.slice(0, 250).replace(/\n+/g, " ") + "...",
    }));

    let ai: GoogleGenAI;
    try {
      ai = getGemini();
    } catch {
      // Grounded offline answer
      const guideTitle = topNotes[0]?.title || "Technical Career Roadmap";
      return res.json({
        answer: `### AI Career Mentor Guidance (Grounded in ${guideTitle})\n\n` +
          `Based on our technical career guides and job market knowledge base:\n\n` +
          `- **Foundational Focus**: Build core programming and problem-solving fundamentals, write clean modular code, and practice version control with Git.\n` +
          `- **Key Skills**: Prioritize modern frameworks, database query optimization (SQL), and automated testing.\n` +
          `- **Curated Guide Excerpt**: "${topNotes[0]?.content.slice(0, 300).replace(/\n/g, " ")}..."\n\n` +
          `*(Connect your \`GEMINI_API_KEY\` to enable dynamic, conversational synthesis)*`,
        sources,
        guardrailTriggered: false,
      });
    }

    const contextText = topNotes.map(n => `--- GUIDE: ${n.title} ---\n${n.content}`).join("\n\n");
    const historyText = history.slice(-5).map((m: any) => `${m.role === "user" ? "Student" : "Mentor"}: ${m.content}`).join("\n");

    const prompt = `You are the SmartHire AI Career Mentor — a supportive, practical career advisor for college students and junior engineers.

GROUNDING DIRECTIVES:
1. Ground your advice in the following RETRIEVED CONTEXT from our vetted career documents.
2. If the context does not contain enough info, state that honestly and provide cautious standard guidance.
3. Structure your answer with clean headings, bullet points, and step-by-step milestones.
4. Reference the source guides where appropriate.

RETRIEVED KNOWLEDGE CONTEXT:
${contextText}

RECENT CONVERSATION HISTORY:
${historyText || "No prior messages."}

STUDENT QUESTION:
${question}

Answer:`;

    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: prompt,
      config: {
        temperature: 0.3,
      },
    });

    res.json({
      answer: response.text || "I was unable to generate an answer. Please check your query.",
      sources,
      guardrailTriggered: false,
    });
  } catch (err: any) {
    console.error("Mentor chat error:", err);
    res.status(500).json({ error: err.message || "Failed to process career mentor query." });
  }
});

// Project Code Viewer Endpoint (Allows inspecting any python file in smarthire-genai)
app.get("/api/code-files", (req, res) => {
  try {
    const listFilesRecursive = (dir: string, base: string = ""): any[] => {
      let results: any[] = [];
      const list = fs.readdirSync(dir);
      list.forEach(file => {
        if (file.startsWith(".") || file === "__pycache__" || file === "venv") return;
        const filePath = path.join(dir, file);
        const relPath = path.join(base, file);
        const stat = fs.statSync(filePath);
        if (stat.isDirectory()) {
          results.push({
            name: file,
            path: relPath,
            type: "directory",
            children: listFilesRecursive(filePath, relPath),
          });
        } else {
          results.push({
            name: file,
            path: relPath,
            type: "file",
            size: stat.size,
          });
        }
      });
      return results;
    };

    const tree = listFilesRecursive(BASE_PROJECT_PATH);
    res.json({ tree });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

app.get("/api/code-content", (req, res) => {
  const filePath = req.query.path as string;
  if (!filePath) return res.status(400).json({ error: "Path required." });

  const safePath = path.normalize(path.join(BASE_PROJECT_PATH, filePath));
  if (!safePath.startsWith(BASE_PROJECT_PATH)) {
    return res.status(403).json({ error: "Access denied." });
  }

  if (fs.existsSync(safePath) && fs.statSync(safePath).isFile()) {
    const content = fs.readFileSync(safePath, "utf-8");
    res.json({ content });
  } else {
    res.status(404).json({ error: "File not found." });
  }
});

// -------------------------------------------------------------
// Vite Middleware / SPA Handler
// -------------------------------------------------------------
async function start() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`SmartHire GenAI Server running on port ${PORT}`);
  });
}

start();
