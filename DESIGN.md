---
name: Mahajan IT Printing Hub
description: A fast, transparent print-order workflow for Dhaka customers.
colors:
  navy: "#0F3863"
  teal: "#00A8B5"
  gold: "#E58E26"
  ink: "#10233B"
  paper: "#F6F8FB"
  white: "#FFFFFF"
  field-border: "#D6E0E9"
  muted: "#8395A6"
  teal-wash: "#E8FBFA"
  teal-deep: "#075E69"
typography:
  display:
    fontFamily: "Instrument Sans, Inter, system-ui, sans-serif"
    fontSize: "clamp(2.4rem, 6vw, 5.2rem)"
    fontWeight: 800
    lineHeight: 0.98
    letterSpacing: "-0.05em"
  body:
    fontFamily: "Instrument Sans, Inter, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.6
rounded:
  sm: "12px"
  md: "18px"
  lg: "28px"
spacing:
  sm: "8px"
  md: "16px"
  lg: "24px"
components:
  button-primary:
    backgroundColor: "{colors.teal}"
    textColor: "{colors.white}"
    rounded: "{rounded.sm}"
    padding: "14px 20px"
  button-secondary:
    backgroundColor: "{colors.navy}"
    textColor: "{colors.white}"
    rounded: "{rounded.sm}"
    padding: "14px 20px"
---

# Design System: Mahajan IT Printing Hub

## Overview

**Creative North Star: "The Print Counter, Rebuilt for the Pocket"**

The interface translates the confidence of a well-run Nilkhet print counter into a clear mobile workflow. Dark navy creates a dependable workbench, teal marks forward movement and help, and gold is reserved for money, confirmations, and high-value actions. The page uses strong typographic contrast and layered paper-like surfaces instead of generic glass cards.

**Key Characteristics:**
- High-contrast navy workbench with bright paper surfaces
- Teal progress and support signals
- Gold reserved for pricing and confirmation
- Short, direct Bangla-first labels with English service terms where familiar
- Functional motion only: file drop, step transitions, and confirmation

## Colors

Navy owns navigation and the bill; teal owns action and support; gold owns money and success. Surfaces stay cool and quiet so the workflow remains legible.

### Primary
- **Nilkhet Navy** (#0F3863): Header, hero workbench, summary panel, and primary trust surfaces.
- **Counter Teal** (#00A8B5): Main actions, progress, links, focus rings, and WhatsApp affordances.
- **Receipt Gold** (#E58E26): Totals, payment emphasis, and confirmation moments.

### Neutral
- **Paper** (#F6F8FB): Page background.
- **White** (#FFFFFF): Form surfaces and readable content zones.
- **Ink** (#10233B): Body copy and high-contrast headings.

## Typography

**Display Font:** Instrument Sans (with Inter/system fallback)

**Body Font:** Instrument Sans (with Inter/system fallback)

**Character:** Dense, friendly, and operational. Headlines are compact and confident; body copy stays readable at mobile sizes.

### Hierarchy
- **Display** (800, clamp(2.4rem, 6vw, 5.2rem), 0.98): Hero promise and confirmation order ID.
- **Headline** (750, 2rem, 1.08): Section and wizard titles.
- **Body** (400, 1rem, 1.6): Instructions and form help, typically 65–75ch.
- **Label** (700, 0.78rem, 1.2): Step labels, metadata, and field labels.

## Layout

The public page is a single-column mobile-first flow that becomes a two-column workbench above 1024px: the wizard occupies the main column while the bill and support context remain visible in a sticky side rail. Navigation collapses into a compact action row on small screens. All controls maintain a comfortable 44px minimum target.

## Elevation & Depth

Depth is structural rather than decorative. Large navy zones create the primary plane; white surfaces sit above it with soft offset shadows. Hover states use a small translate and shadow change, never glow-only decoration.

## Shapes

Controls use 12px corners, larger 18px corners for major surfaces, and 28px corners only for the hero workbench. Borders are cool blue-gray and become teal on focus. Avoid excessive pills except for status, progress, and compact metadata.

## Components

- **Primary button:** Teal fill, white text, arrow/icon cue, clear disabled and loading states.
- **Secondary button:** Navy fill or quiet outline for back, tracking, and utility actions.
- **Field:** White surface, 1px border, explicit label, visible focus ring, helpful error line.
- **Wizard stepper:** Teal active state, navy completed state, muted upcoming state.
- **Bill panel:** Navy surface with gold total and itemized rows.
- **Notice:** Gold-tinted callout for manual support and file-size exceptions.

## Do's and Don'ts

- Do make the next action obvious at every step.
- Do show the exact charge breakdown before payment.
- Do preserve the phone number and specialist-service notice.
- Do keep the wizard usable with keyboard and touch.
- Don't hide pricing behind a modal or an unexplained action.
- Don't use generic stock imagery, fabricated testimonials, or decorative gradients.
