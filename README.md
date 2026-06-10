
<div align="center">

# ⚡ MORSE TRANSMITTER

### A Morse Code Communication Toolkit

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=24&pause=1000&color=00FF41&center=true&vCenter=true&width=700&lines=Text+%E2%86%94+Morse+Translator;Audio+Morse+Transmission;Binary+Encoding+System;Built+with+Python" />

<br>

![Python](https://img.shields.io/badge/Python-3.x-00ff41?style=for-the-badge&logo=python)
![Platform](https://img.shields.io/badge/Platform-Windows-00ff41?style=for-the-badge&logo=windows)
![Status](https://img.shields.io/badge/Status-Active-00ff41?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-00ff41?style=for-the-badge)


</div>

---

# Terminal Preview

```bash
=================================================
         MORSE TRANSMITTER v1.0
=================================================

[A] MORSE MODE
[B] BINARY MODE

> A

ENTER TEXT:
HELLO WORLD

.... . .-.. .-.. --- | .-- --- .-. .-.. -..
```

---

# Features

```diff
+ Text → Morse Translation
+ Morse → Text Translation
+ Real Audio Transmission (Beep)
+ Morse → Binary Conversion
+ Binary → Morse Restoration
+ Supports A-Z and 0-9
+ Word Separation
```

---

# Screenshots

### Terminal Interface

```text
┌───────────────────────────────────────┐
│ MORSE TRANSMITTER                     │
├───────────────────────────────────────┤
│ Input  : HELLO                        │
│ Output : .... . .-.. .-.. ---         │
└───────────────────────────────────────┘
```

### Binary Conversion

```text
HELLO

↓ Morse

.... . .-.. .-.. ---

↓ Binary

0000 0 0100 0100 111
```

---

# Architecture

```mermaid
flowchart LR

A[Text Input]
--> B[Morse Encoder]

B --> C[Audio Beep Engine]

B --> D[Binary Converter]

D --> E[Binary Decoder]

E --> F[Morse Decoder]

F --> G[Text Output]
```

---

# Installation

```bash
git clone https://github.com/Rwin-X/Morse-Transmitter.git

cd Morse-Transmitter

python morse_REAL.py
```

---

# Project Structure

```bash
Morse-Transmitter
│
├── morse_REAL.py
│
├── README.md

---

# Example Usage

## Text → Morse

```text
Input:
CYBER

Output:
-.-. -.-- -... . .-.
```

---

## Morse → Text

```text
Input:
-.-. -.-- -... . .-.

Output:
cyber
```

---

## Morse → Binary

```text
Input:
.-

Output:
01
```

---

# Supported Characters

| Character | Morse |
|-----------|--------|
| A | .- |
| B | -... |
| C | -.-. |
| D | -.. |
| E | . |
| F | ..-. |
| G | --. |
| H | .... |
| I | .. |
| J | .--- |
| K | -.- |
| L | .-.. |
| M | -- |
| N | -. |
| O | --- |
| P | .--. |
| Q | --.- |
| R | .-. |
| S | ... |
| T | - |
| U | ..- |
| V | ...- |
| W | .-- |
| X | -..- |
| Y | -.-- |
| Z | --.. |

---

# Tech Stack

<div align="center">

<img src="https://skillicons.dev/icons?i=python,git,github,vscode" />

</div>

---

# GitHub Statistics

<div align="center">

<img height="180em" src="https://github-readme-stats.vercel.app/api?username=YOUR_USERNAME&show_icons=true&theme=chartreuse-dark"/>

<img height="180em" src="https://github-readme-stats.vercel.app/api/top-langs/?username=YOUR_USERNAME&layout=compact&theme=chartreuse-dark"/>

</div>

---

# Contribution

```bash
Fork
 └── Create Branch
      └── Commit Changes
           └── Push
                └── Pull Request
```

---

# Author

```yaml
Name: Rwin-X
Field: text to morse
Language: Python

```
---

# License

MIT License

---

<div align="center">

```text
01000100 01001001 01010011 01000011 01001001 01010000 01001100 01001001 01001110 01000101

OR

01000100 01000101 01000001 01010100 01001000
```

⭐ Star the repository if you like it.

</div>
