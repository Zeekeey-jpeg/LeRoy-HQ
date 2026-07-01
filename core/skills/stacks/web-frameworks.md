---
name: web-frameworks
description: |
  Build modern full-stack web applications with Next.js, Turborepo, and RemixIcon.

  Use when:
  - Creating React applications with App Router
  - Implementing server-side rendering (SSR, SSG, ISR)
  - Setting up monorepos with Turborepo
  - Optimizing build performance
  - Adding icons to projects
  - Working with TypeScript full-stack projects

  Includes: Next.js 14+, Turborepo, RemixIcon.
---

# Web Frameworks Skill

Comprehensive guide for Next.js, Turborepo, and RemixIcon.

## Stack Selection

### Single App: Next.js + RemixIcon
```bash
npx create-next-app@latest my-app
npm install remixicon
```

### Monorepo: Turborepo + Next.js
```bash
npx create-turbo@latest my-monorepo
```

## Next.js Patterns

### App Router Structure
```
app/
├── layout.tsx       # Root layout
├── page.tsx         # Home page
├── loading.tsx      # Loading UI
├── error.tsx        # Error boundary
└── posts/
    ├── page.tsx     # /posts
    └── [slug]/
        └── page.tsx # /posts/:slug
```

### Server vs Client Components
```tsx
// Server Component (default) - data fetching, no interactivity
async function Posts() {
  const posts = await getPosts(); // Direct async
  return <ul>{posts.map(p => <li key={p.id}>{p.title}</li>)}</ul>
}

// Client Component - interactivity required
'use client'
function Counter() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>
}
```

### Data Fetching
```tsx
// Static (cached forever)
fetch(url, { cache: 'force-cache' })

// Revalidate every hour
fetch(url, { next: { revalidate: 3600 } })

// Dynamic (no cache)
fetch(url, { cache: 'no-store' })
```

### Route Handlers (API Routes)
```tsx
// app/api/users/route.ts
import { NextResponse } from 'next/server'

export async function GET() {
  const users = await getUsers()
  return NextResponse.json(users)
}

export async function POST(request: Request) {
  const body = await request.json()
  const user = await createUser(body)
  return NextResponse.json(user, { status: 201 })
}
```

### Metadata
```tsx
// Static
export const metadata = {
  title: 'My App',
  description: 'App description'
}

// Dynamic
export async function generateMetadata({ params }) {
  const post = await getPost(params.slug)
  return { title: post.title }
}
```

## Turborepo Patterns

### turbo.json Pipeline
```json
{
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": [".next/**", "dist/**"]
    },
    "dev": { "cache": false, "persistent": true },
    "lint": {},
    "test": { "dependsOn": ["build"] }
  }
}
```

### Monorepo Structure
```
my-monorepo/
├── apps/
│   ├── web/           # Next.js app
│   └── admin/         # Admin dashboard
├── packages/
│   ├── ui/            # Shared components
│   ├── config/        # ESLint, TS configs
│   └── types/         # Shared types
└── turbo.json
```

### Shared Packages
```json
// packages/ui/package.json
{
  "name": "@repo/ui",
  "exports": {
    "./button": "./src/button.tsx",
    "./card": "./src/card.tsx"
  }
}

// apps/web/package.json
{
  "dependencies": {
    "@repo/ui": "workspace:*"
  }
}
```

### Remote Caching
```bash
# Login to Vercel for remote cache
npx turbo login

# Link to team
npx turbo link

# Build with remote cache
turbo build
```

## RemixIcon Usage

### Webfont (CSS)
```html
<link href="https://cdn.jsdelivr.net/npm/remixicon/fonts/remixicon.css" rel="stylesheet">

<i class="ri-home-line"></i>
<i class="ri-search-fill ri-2x"></i>
```

### React Component
```tsx
import { RiHomeLine, RiSearchFill } from "@remixicon/react"

<RiHomeLine size={24} />
<RiSearchFill className="text-blue-500" />
```

### Icon Naming Convention
- `-line` = Outlined style
- `-fill` = Filled style
- Categories: System, User, Weather, Media, etc.

## Best Practices

1. **Default to Server Components** - Use Client only for interactivity
2. **Implement loading.tsx** - Automatic Suspense boundaries
3. **Cache aggressively** - Set proper revalidation
4. **Remote caching for teams** - Turborepo cloud cache
5. **Consistent icons** - Line for minimal, Fill for emphasis
6. **Parallel routes** - Use @folder for modals, sidebars
7. **Route groups** - Use (folder) for organization without URL impact

## Performance Optimization

```tsx
// Dynamic imports for heavy components
const HeavyChart = dynamic(() => import('./Chart'), {
  loading: () => <Skeleton />,
  ssr: false
})

// Image optimization
import Image from 'next/image'
<Image src="/photo.jpg" width={800} height={600} alt="Photo" />

// Font optimization
import { Inter } from 'next/font/google'
const inter = Inter({ subsets: ['latin'] })
```

## Common Commands

```bash
# Development
npm run dev           # Start dev server
turbo dev             # Start all apps in monorepo

# Build
npm run build         # Production build
turbo build           # Build all packages

# Lint/Test
turbo lint            # Lint all packages
turbo test            # Test all packages
```
