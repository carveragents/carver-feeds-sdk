# How to Write Claude Skills

## What is a Claude Skill?

A Claude skill is a **directory containing a SKILL.md file** with organized instructions, scripts, and resources that extend Claude's capabilities for specific domains or tasks. Skills enable Claude to handle specialized workflows without requiring all context to be loaded upfront.

## Core Architecture

### Progressive Disclosure Pattern

Skills use a three-tier disclosure approach to manage context efficiently:

1. **Tier 1: Metadata** - Name and description loaded into Claude's system prompt at startup
2. **Tier 2: Core Instructions** - Full SKILL.md content loaded when Claude determines the skill is relevant
3. **Tier 3+: Referenced Resources** - Additional files (reference docs, forms, scripts) accessed only when needed

This design means **context bundled into a skill is effectively unbounded** - Claude doesn't need to load everything at once.

## File Structure

### Required: SKILL.md

Every skill must have a `SKILL.md` file as its entry point. This file must begin with YAML frontmatter:

```yaml
---
name: skill-name
description: Brief explanation of what this skill does and when to use it
---
```

**Critical**: The metadata (name and description) is preloaded into Claude's system prompt. This allows Claude to recognize when each skill is relevant without consuming full context.

### Optional: Additional Resources

Skills can include:
- **Documentation files** (e.g., `reference.md`, `guidelines.md`)
- **Executable scripts** (e.g., Python, Bash)
- **Configuration files**
- **Templates or forms**
- **Data files**

## How Skills Work

### 1. Skill Discovery

When Claude starts, it loads all skill metadata (names and descriptions) into its system prompt. This enables Claude to:
- Recognize when a user request matches a skill's purpose
- Make informed decisions about which skill to invoke
- Do this without loading full skill content

### 2. Skill Activation

When Claude determines a skill is relevant:
1. Claude uses the Bash tool to read the `SKILL.md` file
2. The skill's full instructions expand into Claude's context
3. Claude follows the instructions in the skill

### 3. Resource Loading

As Claude works through a skill's instructions:
- It selectively loads referenced documentation files as needed
- It executes bundled scripts when appropriate
- It manages context window by loading only what's currently required

### 4. Code Execution

Skills can include **executable scripts** that Claude runs as tools:
- Instead of generating tokens for deterministic operations, Claude executes prewritten code
- Example: A Python script that extracts specific data without loading entire documents into context
- This offloads computation and saves context window space

## Creating a New Skill: Step-by-Step

### Step 1: Identify the Need

Start with evaluation:
- Identify capability gaps through representative testing
- Determine if the task requires specialized knowledge or workflow
- Assess if the task would benefit from bundled scripts or resources

### Step 2: Structure Your Skill

Create a directory in `.claude/skills/`:

```
.claude/
└── skills/
    └── your-skill-name/
        ├── SKILL.md          # Required: Entry point
        ├── reference.md      # Optional: Detailed reference
        ├── scripts/          # Optional: Executable code
        └── templates/        # Optional: Templates or examples
```

### Step 3: Write the SKILL.md

Structure your `SKILL.md` with:

```yaml
---
name: descriptive-skill-name
description: Clear, concise explanation of when and why to use this skill
---

# Skill Instructions

[Core instructions that Claude should follow when this skill is invoked]

## When to Use This Skill

[Describe the scenarios where this skill applies]

## Process

[Step-by-step instructions for Claude to follow]

## Resources

[References to additional files if needed]
- See `reference.md` for detailed documentation
- Use `scripts/process.py` for data extraction

## Guidelines

[Any important constraints or best practices]
```

### Step 4: Think From Claude's Perspective

- **Name**: Choose a name that clearly indicates the skill's purpose
- **Description**: Write from Claude's POV - "Use this when the user asks to..."
- **Instructions**: Be explicit and structured - Claude will follow them precisely
- **Context Management**: Split unwieldy content into separate files that Claude can load selectively

### Step 5: Bundle Executable Code

If your skill needs deterministic operations:
- Write Python/Bash scripts for data processing
- Include clear instructions in SKILL.md for when to execute them
- Let Claude run the scripts rather than generating equivalent code

Example instruction in SKILL.md:
```markdown
To extract form fields, run:
```bash
python scripts/extract_fields.py --input {file_path}
```
```

### Step 6: Test and Iterate

- Test the skill with representative examples
- Monitor how Claude interprets and uses the skill
- Refine the description if Claude misidentifies when to use it
- Ask Claude to document successful approaches and mistakes
- Update the skill based on real-world usage

## Best Practices

### Organization

- **Separate mutually exclusive contexts**: If content is only relevant in specific scenarios, split it into separate files
- **Scale thoughtfully**: Start simple, add complexity only when needed
- **Use clear file names**: Claude will read file names to decide what to load

### Instructions

- **Be explicit**: Claude follows instructions literally
- **Provide structure**: Use headings, lists, and clear steps
- **Include examples**: Show Claude what good output looks like
- **Handle edge cases**: Document how to handle errors or unusual situations

### Context Management

- **Progressive disclosure**: Don't load everything in SKILL.md - reference additional files
- **Minimize redundancy**: Don't duplicate information across files
- **Think in layers**: Core instructions in SKILL.md, detailed reference in separate files

### Code Integration

- **Offload computation**: Use scripts for deterministic operations
- **Clear interfaces**: Document input/output formats for scripts
- **Error handling**: Scripts should fail gracefully with clear error messages

## Security Considerations

**Critical**: Skills have full access to tools and can execute code.

- **Only install skills from trusted sources**
- **Audit all bundled files** before use
- **Review code dependencies** in any scripts
- **Check for external network access** - be cautious of instructions directing Claude to external sources
- **Understand what the skill can do** - read the SKILL.md thoroughly

## Skill Invocation Mechanism

Skills can be invoked in two ways:

1. **Automatic**: Claude recognizes user input matches a skill's description and automatically reads the SKILL.md
2. **Manual**: User can explicitly invoke a skill (implementation varies by platform)

The skill framework relies on:
- Claude's ability to use filesystem tools (Read, Bash)
- Claude's reasoning about when skills are relevant
- The progressive disclosure pattern to manage context

## Platform Support

Skills are currently supported across:
- Claude.ai
- Claude Code
- Claude Agent SDK
- Claude Developer Platform

## Continuous Improvement

As mentioned in Anthropic's engineering article:

> "We iterated closely with Claude, asking it to write down what it had learned about successfully completing the task, and the kinds of mistakes it had made, so we could reuse that information on future runs."

**Key insight**: Let Claude help build skills by documenting successful patterns and common mistakes. This creates a feedback loop for continuous improvement.

---

## Summary

A Claude skill is:
- A directory with a `SKILL.md` file containing YAML frontmatter
- A progressive disclosure system that loads context selectively
- A way to bundle instructions, documentation, and executable code
- An extension of Claude's capabilities for specialized domains

To create a skill:
1. Identify the capability gap
2. Structure files for selective loading
3. Write clear, explicit instructions
4. Bundle executable code for deterministic operations
5. Test and iterate based on real usage
6. Always audit for security before installation

The power of skills lies in **unbounded context** (through progressive loading) and **deterministic execution** (through bundled scripts), enabling Claude to handle complex, specialized workflows efficiently.
