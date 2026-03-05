---
name: react-artifact-builder
description: "Build self-contained React components as single HTML files with Tailwind CSS, using CDN imports and modern hooks patterns"
category: coding
difficulty: intermediate
model_boost: "Weak models create React artifacts that can't run standalone (missing imports, broken styling). This skill ensures every artifact is a complete, immediately-executable single HTML file."
---

# React Artifact Builder

## Purpose
This skill teaches you to create fully functional React applications as single HTML files that run instantly in any browser. This is ideal for shareable prototypes, interactive dashboards, and demos—no build step required. You'll learn to import React and Tailwind from CDNs, manage state with hooks, implement responsive designs, and avoid common pitfalls like localStorage in sandboxed environments. A good artifact is beautiful, functional, and copyable into a text file.

## When to Use
- You need to share a working prototype without deployment complexity
- You want a quick interactive demo for stakeholder feedback
- You're building a utility or tool for immediate use (not production)
- You need responsive UI without build tooling overhead
- **Do NOT use when**: Building a production app (use Next.js/Vite); you need server-side rendering; localStorage persistence is critical (doesn't work in sandboxed contexts)

## Instructions

### Step 1: Set Up the HTML Skeleton
Every React artifact starts with this structure. Don't skip any part—missing even one import breaks execution.

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>App Title</title>
    <!-- Tailwind CSS (no installation required) -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- React 18 (via Babel for JSX) -->
    <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <!-- Babel for JSX transformation -->
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <style>
        /* Custom styles (optional) */
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
    </style>
</head>
<body class="bg-gray-50">
    <div id="root"></div>

    <script type="text/babel">
        // Your React code here
        const { useState, useEffect, useContext, createContext } = React;

        function App() {
            return (
                <div className="p-8">
                    <h1 className="text-3xl font-bold">Hello React!</h1>
                </div>
            );
        }

        const root = ReactDOM.createRoot(document.getElementById('root'));
        root.render(<App />);
    </script>
</body>
</html>
```

**Critical notes:**
- `type="text/babel"` tells Babel to transform JSX before execution
- `const { useState, useEffect, ... } = React` imports hooks into your script scope
- React imports must come BEFORE Babel script
- Always include `crossorigin` attribute on React imports

### Step 2: Build a Stateful Component with Hooks
Use `useState` for local state. Example: a counter.

```jsx
function Counter() {
    const [count, setCount] = useState(0);
    const [history, setHistory] = useState([]);

    const increment = () => {
        setCount(c => c + 1);
        setHistory(h => [...h, count]);  // Append old count to history
    };

    return (
        <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow">
            <h2 className="text-2xl font-bold mb-4">Counter: {count}</h2>
            <button
                onClick={increment}
                className="px-6 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition"
            >
                +1
            </button>
            <div className="mt-6">
                <h3 className="font-semibold mb-2">History:</h3>
                <ul className="text-sm text-gray-600">
                    {history.map((h, i) => <li key={i}>{i + 1}. {h}</li>)}
                </ul>
            </div>
        </div>
    );
}
```

**State rules:**
- Always use the functional form `setCount(c => c + 1)` to avoid stale closures
- Don't mutate state directly: use `[...array]` for arrays, `{...obj}` for objects
- Each `useState` is independent—combine into an object if related:
  ```jsx
  const [form, setForm] = useState({ name: '', email: '' });
  setForm(f => ({ ...f, name: 'John' }));
  ```

### Step 3: Handle Forms and Inputs
Form inputs must update state on change. Standard pattern:

```jsx
function ContactForm() {
    const [form, setForm] = useState({ name: '', email: '', message: '' });
    const [submitted, setSubmitted] = useState(false);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setForm(f => ({ ...f, [name]: value }));
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        console.log('Form submitted:', form);
        setSubmitted(true);
        setTimeout(() => setSubmitted(false), 3000);  // Clear after 3s
    };

    return (
        <form onSubmit={handleSubmit} className="max-w-lg mx-auto p-6 bg-white rounded-lg shadow">
            <div className="mb-4">
                <label className="block text-sm font-semibold mb-2">Name</label>
                <input
                    type="text"
                    name="name"
                    value={form.name}
                    onChange={handleChange}
                    className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Your name"
                />
            </div>
            <div className="mb-4">
                <label className="block text-sm font-semibold mb-2">Email</label>
                <input
                    type="email"
                    name="email"
                    value={form.email}
                    onChange={handleChange}
                    className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="you@example.com"
                />
            </div>
            <div className="mb-6">
                <label className="block text-sm font-semibold mb-2">Message</label>
                <textarea
                    name="message"
                    value={form.message}
                    onChange={handleChange}
                    rows="4"
                    className="w-full px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Your message..."
                />
            </div>
            <button
                type="submit"
                className="w-full px-6 py-2 bg-green-500 text-white rounded font-semibold hover:bg-green-600 transition"
            >
                Send
            </button>
            {submitted && <p className="mt-4 text-green-600 text-center">Message sent!</p>}
        </form>
    );
}
```

**Form patterns:**
- Always `e.preventDefault()` on submit to prevent page reload
- Use `[name]: value` to handle multiple inputs with one handler
- Reset forms with `setForm({ name: '', email: '' })`
- Checkbox: `value={form.agree}` + `onChange={e => setForm(f => ({ ...f, agree: e.target.checked }))}`

### Step 4: Use useEffect for Side Effects
Side effects (API calls, timers, subscriptions) belong in `useEffect`:

```jsx
function FetchUser() {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        let isMounted = true;  // Prevent state updates if component unmounts

        const fetchData = async () => {
            try {
                const response = await fetch('https://jsonplaceholder.typicode.com/users/1');
                const data = await response.json();
                if (isMounted) {
                    setUser(data);
                    setLoading(false);
                }
            } catch (err) {
                if (isMounted) {
                    setError(err.message);
                    setLoading(false);
                }
            }
        };

        fetchData();

        return () => { isMounted = false; };  // Cleanup on unmount
    }, []);  // Empty dependency array = run once on mount

    if (loading) return <p className="p-4">Loading...</p>;
    if (error) return <p className="p-4 text-red-600">Error: {error}</p>;

    return (
        <div className="p-4 bg-white rounded shadow">
            <h3 className="font-bold">{user.name}</h3>
            <p className="text-sm text-gray-600">{user.email}</p>
        </div>
    );
}
```

**useEffect rules:**
- Dependencies `[]` = run once on mount
- Dependencies `[value]` = run when value changes
- No dependency array = run after every render (usually wrong)
- Always return cleanup function if creating subscriptions/timers

### Step 5: Build a Tab/Toggle Navigation
Multi-view apps need conditional rendering:

```jsx
function TabsApp() {
    const [activeTab, setActiveTab] = useState('dashboard');

    const tabs = [
        { id: 'dashboard', label: 'Dashboard', icon: '📊' },
        { id: 'settings', label: 'Settings', icon: '⚙️' },
        { id: 'help', label: 'Help', icon: '❓' },
    ];

    return (
        <div className="h-screen flex flex-col bg-gray-100">
            {/* Header */}
            <header className="bg-white shadow">
                <div className="max-w-4xl mx-auto px-6 py-4">
                    <h1 className="text-2xl font-bold">My App</h1>
                </div>
            </header>

            {/* Tabs */}
            <div className="bg-white border-b">
                <div className="max-w-4xl mx-auto px-6 flex gap-4">
                    {tabs.map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`px-4 py-3 font-semibold border-b-2 transition ${
                                activeTab === tab.id
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-600 hover:text-gray-900'
                            }`}
                        >
                            {tab.icon} {tab.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 max-w-4xl mx-auto w-full px-6 py-8">
                {activeTab === 'dashboard' && <Dashboard />}
                {activeTab === 'settings' && <Settings />}
                {activeTab === 'help' && <Help />}
            </div>
        </div>
    );
}

function Dashboard() {
    return <div className="bg-white p-6 rounded shadow"><h2>Dashboard Content</h2></div>;
}

function Settings() {
    return <div className="bg-white p-6 rounded shadow"><h2>Settings Content</h2></div>;
}

function Help() {
    return <div className="bg-white p-6 rounded shadow"><h2>Help Content</h2></div>;
}
```

### Step 6: Implement Responsive Design with Tailwind
Tailwind breakpoints: `sm` (640px), `md` (768px), `lg` (1024px), `xl` (1280px).

```jsx
function ResponsiveGrid() {
    const items = [
        { id: 1, title: 'Item 1', desc: 'Description 1' },
        { id: 2, title: 'Item 2', desc: 'Description 2' },
        { id: 3, title: 'Item 3', desc: 'Description 3' },
        { id: 4, title: 'Item 4', desc: 'Description 4' },
    ];

    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 p-4">
            {items.map(item => (
                <div key={item.id} className="bg-white p-4 rounded-lg shadow hover:shadow-lg transition">
                    <h3 className="font-bold text-lg">{item.title}</h3>
                    <p className="text-sm text-gray-600">{item.desc}</p>
                    <button className="mt-4 w-full px-4 py-2 bg-blue-500 text-white rounded text-sm font-semibold hover:bg-blue-600">
                        View
                    </button>
                </div>
            ))}
        </div>
    );
}
```

### Step 7: Avoid localStorage (Sandboxed Environments)
Many artifact runners (like Claude artifacts) use sandboxed iframes—localStorage won't persist. Use state instead or sync to an external API.

**Instead of:**
```jsx
// This won't work in sandboxes
localStorage.setItem('count', count);
```

**Do this:**
```jsx
// Use state (works everywhere)
const [count, setCount] = useState(0);

// Or sync to API
useEffect(() => {
    fetch('/api/save', { method: 'POST', body: JSON.stringify({ count }) });
}, [count]);
```

### Step 8: Add Error Boundaries (Optional but Good)
Catch component crashes:

```jsx
class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true };
    }

    render() {
        if (this.state.hasError) {
            return <div className="p-4 bg-red-100 text-red-700 rounded">Something went wrong.</div>;
        }
        return this.props.children;
    }
}

// Wrap your main app
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
    <ErrorBoundary>
        <App />
    </ErrorBoundary>
);
```

### Step 9: Optimize Performance (Conditionally)
For artifacts with 50+ items or complex calculations, use `useMemo`:

```jsx
function HeavyList({ items, filter }) {
    const filtered = React.useMemo(
        () => items.filter(i => i.name.includes(filter)),
        [items, filter]  // Recalculate only if items or filter changes
    );

    return (
        <ul>
            {filtered.map(item => <li key={item.id}>{item.name}</li>)}
        </ul>
    );
}
```

### Step 10: Test Your Artifact
Copy the entire HTML file into:
1. A `.html` file and open in browser
2. An artifact viewer or sandbox
3. Share the raw HTML text with collaborators

Verify:
- Page loads without errors (check browser console)
- All buttons and forms respond
- Responsive design works (resize browser)
- No 404s or failed imports (check Network tab)

## Output Template

A complete React artifact includes:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>App Name</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
</head>
<body class="bg-gray-50">
    <div id="root"></div>
    <script type="text/babel">
        const { useState, useEffect } = React;

        function App() {
            // Your components here
        }

        const root = ReactDOM.createRoot(document.getElementById('root'));
        root.render(<App />);
    </script>
</body>
</html>
```

## Quality Gates
- [ ] HTML file loads without console errors
- [ ] All React hooks are imported from React object at top of script
- [ ] useState, useEffect, or other hooks work correctly
- [ ] Forms prevent default behavior (e.preventDefault)
- [ ] At least one interactive element (button, form, or toggle)
- [ ] Tailwind CSS classes are applied and visible
- [ ] No references to external CSS files or build tools
- [ ] Artifact works when saved as .html and opened in browser
- [ ] Component is responsive (works on mobile and desktop viewports)

## Examples

### Good Output (excerpt)
```jsx
function App() {
    const [items, setItems] = useState([]);
    const [input, setInput] = useState('');

    const addItem = () => {
        if (input.trim()) {
            setItems([...items, { id: Date.now(), text: input }]);
            setInput('');
        }
    };

    return (
        <div className="max-w-md mx-auto p-6">
            <input
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyPress={e => e.key === 'Enter' && addItem()}
                className="w-full px-4 py-2 border rounded"
            />
            <button onClick={addItem} className="mt-2 px-4 py-2 bg-blue-500 text-white rounded">Add</button>
            <ul className="mt-4">
                {items.map(item => <li key={item.id}>{item.text}</li>)}
            </ul>
        </div>
    );
}
```
✓ Uses hooks correctly ✓ Prevents default form behavior ✓ State updates properly

### Bad Output (what to avoid)
```jsx
function App() {
    let items = [];  // ✗ Won't trigger re-renders, use useState

    return (
        <div>
            <input onChange={e => items.push(e.target.value)} />
            {items.map(item => <li>{item}</li>)}
        </div>
    );
}
```
✗ Mutates state directly ✗ No hooks ✗ No styling

## Common Mistakes

1. **Mistake:** Forgetting `type="text/babel"` on script tag → **Fix:** Babel won't transform JSX without it. Always include `<script type="text/babel">`.

2. **Mistake:** Using class components when hooks are available → **Fix:** Use functional components with hooks (simpler, less boilerplate).

3. **Mistake:** Mutating state directly (`items.push(x)` instead of `[...items, x]`) → **Fix:** Always create new arrays/objects. React won't detect mutations.

4. **Mistake:** localStorage data disappearing in sandboxes → **Fix:** Use component state instead. Artifacts often run in iframes where localStorage doesn't persist.

5. **Mistake:** Importing non-existent packages → **Fix:** Only use React, React-DOM, and libraries available on CDN (check cdnjs.com).

6. **Mistake:** Not handling loading/error states in useEffect → **Fix:** Always include loading and error states when fetching data.

## Anti-Patterns

- Never use class components (harder to read, more boilerplate)
- Never import npm packages directly (only use CDN imports)
- Never forget the Babel script (JSX won't compile)
- Never skip the `key` prop in lists (causes re-render bugs)
- Never mutate state directly—always create new objects/arrays
