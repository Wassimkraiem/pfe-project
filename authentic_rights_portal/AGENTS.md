# Repository Guidelines

## Project Structure & Module Organization
- `src/app` holds Next.js App Router pages and layouts. Routes map to folders (e.g., `src/app/signup/page.tsx`).
- `src/components` contains shared UI components (PascalCase filenames).
- `src/theme` defines the MUI theme (`palette.ts`, `typography.ts`, `components.ts`).
- `src/lib` and `src/hooks` contain shared utilities and React hooks.
- Static assets live in `public/`.

## Build, Test, and Development Commands
- `npm run dev` starts the local dev server at `http://localhost:3000`.
- `npm run build` creates the production build.
- `npm run start` serves the production build locally.
- `npm run lint` runs ESLint.
- `npm run format` formats the repo with Prettier; `npm run format:check` verifies formatting.

## Coding Style & Naming Conventions
- TypeScript is the default; keep components and pages in `.tsx`.
- Indentation is 2 spaces (Prettier). Run `npm run format` before committing.
- Components use PascalCase (e.g., `StepIndicator.tsx`), theme files use camelCase (e.g., `palette.ts`).
- Prefer MUI `sx` prop for component-level styling to stay consistent with the theme.

## Testing Guidelines
- No automated test framework is configured in this repository yet.
- If you add tests, colocate them with the feature (`*.test.tsx`) or under a `__tests__/` folder and document the new command in this file.

## Commit & Pull Request Guidelines
- Recent commit messages are sentence-style, descriptive, and start with a verb (e.g., “Add…”, “Refactor…”). Keep that pattern.
- PRs should include a short summary, testing notes (commands run), and screenshots or screen recordings for UI changes.
- Link relevant issues or tickets in the PR description when applicable.

## Security & Configuration Tips
- Configure environment variables in `.env.local` (see `.env.example`).
- Do not commit secrets; use Netlify environment variables for deployments.
