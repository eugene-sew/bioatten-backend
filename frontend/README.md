# Frontend - Vite + React + Tailwind CSS

## ✅ Setup Complete

This frontend project has been scaffolded with the following tools and configurations:

### 🛠️ Tech Stack

- **Vite** - Build tool and dev server
- **React** - UI library
- **Tailwind CSS** - Utility-first CSS framework
- **Zustand** - State management
- **Axios** - HTTP client
- **React Router v6** - Routing
- **React Hook Form** - Form handling
- **Recharts** - Charts library

### 📦 Development Tools

- **ESLint** with Airbnb configuration
- **Prettier** for code formatting
- **Absolute imports** configured with `@/` alias

## 🚀 Getting Started

```bash
# Install dependencies (already done)
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## 🧹 Linting & Formatting

```bash
# Run ESLint
npm run lint

# Fix ESLint issues
npm run lint:fix

# Format code with Prettier
npm run format

# Check formatting
npm run format:check
```

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/       # Reusable components
│   │   └── Button.jsx   # Example component
│   ├── App.jsx          # Main app component
│   ├── main.jsx         # Entry point
│   └── index.css        # Tailwind CSS imports
├── .eslintrc.cjs        # ESLint configuration
├── .prettierrc          # Prettier configuration
├── tailwind.config.js   # Tailwind configuration
├── postcss.config.js    # PostCSS configuration
├── vite.config.js       # Vite configuration
└── jsconfig.json        # JS configuration for absolute imports
```

## 🎯 Using Absolute Imports

You can import components using the `@/` alias:

```jsx
import Button from '@/components/Button';
import useStore from '@/store/useStore';
```

## 🎨 Tailwind CSS

Tailwind CSS is configured and ready to use. The configuration file is at `tailwind.config.js`.

Example usage:
```jsx
<div className="bg-blue-500 text-white p-4 rounded-lg">
  Hello Tailwind!
</div>
```

## 📝 Example Components

A simple Button component has been created at `src/components/Button.jsx` as an example of:
- Using Tailwind CSS classes
- ESLint/Prettier compliant code
- Proper component structure

The main App component demonstrates:
- Absolute imports using `@/` alias
- Tailwind CSS styling
- React hooks usage
- Clean component structure

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.
