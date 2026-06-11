---
name: Forge Industrial v2.0
colors:
  surface: '#f7faf5'
  surface-dim: '#d8dbd6'
  surface-bright: '#f7faf5'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f1f4f0'
  surface-container: '#ecefea'
  surface-container-high: '#e6e9e4'
  surface-container-highest: '#e0e3df'
  on-surface: '#191c1a'
  on-surface-variant: '#5a403c'
  inverse-surface: '#2d312e'
  inverse-on-surface: '#eff2ed'
  outline: '#8f706b'
  outline-variant: '#e3beb8'
  surface-tint: '#F75440'
  primary: '#F75440'
  on-primary: '#ffffff'
  primary-container: '#F75440'
  on-primary-container: '#fffbff'
  inverse-primary: '#ffb4a8'
  secondary: '#051F13'
  on-secondary: '#ffffff'
  secondary-container: '#ccead6'
  on-secondary-container: '#ccead6'
  tertiary: '#00666b'
  on-tertiary: '#ffffff'
  tertiary-container: '#008287'
  on-tertiary-container: '#f4ffff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdad4'
  primary-fixed-dim: '#ffb4a8'
  on-primary-fixed: '#410000'
  on-primary-fixed-variant: '#920401'
  secondary-fixed: '#051F13'
  secondary-fixed-dim: '#b0cdba'
  on-secondary-fixed: '#ffffff'
  on-secondary-fixed-variant: '#324c3e'
  tertiary-fixed: '#81f4fb'
  tertiary-fixed-dim: '#63d7de'
  on-tertiary-fixed: '#002022'
  on-tertiary-fixed-variant: '#004f53'
  background: '#f7faf5'
  on-background: '#191c1a'
  surface-variant: '#e0e3df'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 48px
    fontWeight: '800'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '800'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  data-tabular:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 48px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 40px
---

## Brand & Style
The design system is engineered for manufacturing decision-makers who require immediate clarity and professional rigor. The brand personality is industrial, high-contrast, and authoritative, balancing the raw energy of a factory floor with the precision of high-level analytics. 

The aesthetic leverages **Modern Industrial Minimalism**. It utilizes heavy visual weights and crisp intersections to evoke a sense of structural integrity. While the palette is vibrant, the application remains systematic and utility-driven, ensuring that every visual element serves a functional purpose in high-stakes operational environments.

## Colors
This design system employs a high-contrast palette designed for legibility in varied lighting conditions.

*   **Primary (Coral-Orange `#F75440`):** Used for critical actions, alerts, CTAs, and primary branding elements. It signifies energy and urgency.
*   **Secondary (Deep Forest `#051F13`):** Used for navigation backgrounds, footers, anchor sections, and stable state indicators. It provides a grounded, professional anchor.
*   **Surface (Warm Grey):** The foundational layer for all application screens, chosen to reduce eye strain compared to pure white while maintaining a clean, modern feel.
*   **Neutral (Slate Carbon):** Used for primary text and iconography to ensure a strong contrast ratio against the warm grey surface.

## Typography
The typography strategy distinguishes between **Executive Summary** (Plus Jakarta Sans) and **Operational Data** (Inter). 

Headlines use Plus Jakarta Sans with tighter tracking and heavier weights to command attention. For data-heavy environments, tables, and technical readouts, Inter provides the necessary neutrality and legibility. Use `data-tabular` for all numerical values in dashboards to ensure alignment and rapid scanning.

## Layout & Spacing
The layout follows a **Fixed-Fluid Hybrid Grid**. Content is housed within a 12-column grid on desktop (max-width 1440px) that centers on larger displays. 

A strict 4px baseline grid governs all vertical rhythm. 
*   **Desktop:** 12 columns, 24px gutters, 40px side margins.
*   **Tablet:** 8 columns, 16px gutters, 24px side margins.
*   **Mobile:** 4 columns, 16px gutters, 16px side margins.

Spacing between functional groups should typically be `xl` (48px), while spacing between elements within a group should use `md` (16px) or `sm` (8px).

## Elevation & Depth
This design system uses **Tonal Layering** supplemented by **Low-Contrast Outlines** to define hierarchy, moving away from soft shadows to maintain an industrial, "machined" look.

*   **Level 0 (Base):** Surface (#F9F9F9).
*   **Level 1 (Cards/Containers):** Pure White (#FFFFFF) with a 1px solid border in #E0E0E0. No shadow.
*   **Level 2 (Dropdowns/Modals):** Pure White with a subtle, 4px direct "hard" shadow (Opacity 10%, Black) to simulate a physical object resting on a surface.
*   **Level 3 (Interactive):** Primary Coral-Orange accents define the "active" elevation through color intensity rather than shadow depth.

## Shapes
Shapes are geometric and sturdy. The system avoids extreme "pill" shapes to maintain a professional, industrial character.

*   **Small Components (Buttons, Inputs):** 8px (md) radius.
*   **Medium Components (Cards, Modals):** 16px (lg) radius.
*   **Large Layout Blocks (Section Wrappers):** 24px (xl) radius.
*   **Icons:** Use a 2px stroke weight with slightly rounded joins to match the component radius.

## Components
*   **Buttons:** Primary buttons use Coral-Orange (`#F75440`) with white text. Secondary buttons use Deep Forest (`#051F13`) with white text. All buttons have a height of 48px for high hit-volume industrial use.
*   **Input Fields:** Use White backgrounds with a 1px border. On focus, the border thickens to 2px in Deep Forest (`#051F13`). Labels are always positioned above the field using `label-sm`.
*   **Cards:** Use White backgrounds, 16px radius, and 24px internal padding. Headers within cards should have a subtle bottom border separator.
*   **Chips/Status Tags:** Use high-contrast fills for status (e.g., Deep Forest for 'Optimal', Coral-Orange for 'Critical'). Text inside chips should be bold and 12px.
*   **Data Grids:** Use Inter for all cell content. Zebra-striping is permitted using a 2% tint of Obsidian Green on alternate rows for high-density scanning.
*   **KPI Widgets:** Display large numerical values using `display-lg` to ensure they are readable from a distance on factory floor monitors.