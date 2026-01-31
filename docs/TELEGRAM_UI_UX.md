# Telegram Bot UI/UX Audit & Redesign

## 1. Audit of Existing Interface
**Current State:**
- **Structure:** 4x2 Grid (8 buttons).
- **Chaos Factors:**
  - **Inconsistent Grouping:** "Fear/Greed" (Analysis) mixed with "Calculator" (Tool).
  - **Missing Features:** Newly implemented Calendar, Alerts, and Events are accessible only via text commands (`/kalendarz`, `/alerts`), not the visual menu.
  - **Hidden Complexity:** "Admin" takes up prime real estate in the main menu.
  - **Label Clarity:** "Sygnały" is vague (should be "Aktywne Sygnały").

## 2. Design System Principles
- **Hierarchy:** Primary actions (Trading) > Analysis > Tools > System.
- **Iconography:** Consistent emoji usage as visual anchors.
  - 🚀/🔥 = Action/Trading
  - 📊/😱 = Analysis/Data
  - 🧮/📅 = Tools/Planning
  - 👤/💼 = Personal/Assets
- **Navigation:** Deep navigation with "Back" (🔙) buttons for submenus.

## 3. Design Proposals

### Variant A: Simplified (Focus on Focus)
*For the trader who wants zero noise.*
- **Row 1:** 🔥 Top 3 Okazje | 💼 Mój Portfel
- **Row 2:** 📅 Kalendarz | 😱 Strach/Chciwość
- **Row 3:** 👤 Profil | ❓ Pomoc

### Variant B: Advanced (The "Bloomberg Terminal" Lite) - **RECOMMENDED**
*Structured categorization for full access.*
- **Row 1 [Trading]:** 🔥 Top 3 | 🚀 Sygnały | 💼 Portfel
- **Row 2 [Analiza]:** 📅 Kalendarz | 😱 Fear Index | 🗞️ News
- **Row 3 [Narzędzia]:** 🧮 Kalkulator | 🔔 Alerty | ⚙️ Admin
- **Row 4 [Edukacja]:** 📚 Baza Wiedzy | 👤 Profil

### Variant C: Personalized (Task-Based)
*Organized by workflow stages.*
- **Row 1 [Start Dnia]:** ☕ Briefing | 📅 Kalendarz
- **Row 2 [Szukanie]:** 🔥 Skaner | 🔔 Alerty
- **Row 3 [Egzekucja]:** 🧮 Kalkulator | 💼 Portfel

## 4. Implementation Plan (Advanced Variant)
We will implement **Variant B** to accommodate the new Calendar and Alert features while maintaining order.

**New Menu Structure:**
1.  **Main Menu:**
    -   Row 1: Trading (Top 3, Signals, Portfolio)
    -   Row 2: Analysis (Calendar, Fear, Events)
    -   Row 3: Tools (Calc, Alerts, Admin)
    -   Row 4: Profile/Edu (Profile, Learn)

**Sub-Menus needed:**
-   **Calendar Menu:** Today, Tomorrow, This Week, Alerts.
