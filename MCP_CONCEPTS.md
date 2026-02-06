# What is MCP? Why do we need it? 🤖🔌

Welcome! If you are new to AI or this project, this document explains the core concepts in the simplest way possible.

## 1. What is MCP? (Simple Explanation)

**MCP (Model Context Protocol)** is like a **"USB port"** for Artificial Intelligence (AI).

Imagine this:

- **AI (like ChatGPT, Claude, Gemini)** is a super-smart brain, but it is "locked" inside Google/OpenAI servers. It knows nothing about your internal data, Excel files, or company databases.
- **Your Data (Oracle Database)** is the treasure chest containing vital information.

👉 **MCP Server** acts as the **translator** in the middle. It helps AI securely "connect" to your data to read, search, and analyze it for you.

## 2. What is this Server for?

This project (`mcp-oracle-server`) is a tool that enables AI to "talk" to our **Oracle** database management system.

Instead of writing complex SQL queries yourself, you can simply ask the AI in plain English:

> _"Find all unpaid invoices for customer John Doe from this month."_

Here is what happens behind the scenes:

1. AI receives your request.
2. AI asks the **MCP Server** to locate the "Invoices" table.
3. AI asks the **MCP Server** to run a safe search query.
4. AI summarizes the results and answers you.

## 3. Is it Safe? 🛡️

**Yes, very safe.** We have implemented multiple layers of protection:

- **Read-only**: By default, AI is mostly used to read data to answer questions.
- **Human-in-the-loop**: If the AI needs to modify data (insert, delete), it **MUST** ask for your permission and wait for you to click "Approve" before proceeding.
- **Blocked Dangerous Commands**: Commands like "Delete Database" (DROP DATABASE) are completely banned.

## 4. What do I need to do?

Simply follow the instructions in the main **[README.md](README.md)** to install it once. After that, you can open your AI tools (like Cursor, Windsurf, Claude Desktop) and start working with your data 10x faster!

---

[Back to Main Page](README.md)
