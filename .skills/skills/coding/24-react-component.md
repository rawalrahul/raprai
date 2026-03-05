---
name: react-component
description: "Generate production React components with TypeScript, modern hooks, error boundaries, accessibility (ARIA), Storybook stories, and comprehensive unit tests."
category: coding
difficulty: intermediate
model_boost: "Weak models create inaccessible React components, missing error handling, or poor TypeScript practices"
---

# React Component

## Purpose
This skill generates production-grade React components written in TypeScript that follow modern best practices. Components include proper type definitions, custom hooks where appropriate, error boundary implementation, accessibility (WCAG 2.1) compliance with ARIA attributes, Storybook documentation with interactive stories, unit tests with React Testing Library, and responsive design patterns. Output components are immediately usable in enterprise applications with comprehensive test coverage and documentation.

## When to Use
- Building reusable UI components for design systems
- Creating components for new React applications or features
- Refactoring existing JavaScript components to TypeScript
- Implementing accessible form components, dialogs, and navigation
- Setting up Storybook for component-driven development
- Creating tested, well-documented components for team use
- **Do NOT use when**: Building Angular or Vue components, or legacy React class components

## Instructions

### Step 1: Define Component Interface and Props
Design TypeScript interfaces for strong type safety:

```typescript
// Types
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'small' | 'medium' | 'large';
  isLoading?: boolean;
  icon?: React.ReactNode;
  children: React.ReactNode;
}

interface FormInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange' | 'value'> {
  label: string;
  error?: string;
  required?: boolean;
  value: string;
  onChange: (value: string) => void;
  helperText?: string;
}

interface DataTableProps<T extends Record<string, any>> {
  columns: Array<{
    key: keyof T;
    label: string;
    sortable?: boolean;
    render?: (value: T[keyof T], row: T) => React.ReactNode;
  }>;
  data: T[];
  onRowClick?: (row: T) => void;
  loading?: boolean;
  error?: string;
}
```

### Step 2: Create Base Component with Hooks
Implement component logic with modern React hooks:

```typescript
import React, { useState, useCallback, useReducer, ReactNode } from 'react';
import styles from './Button.module.css';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'small' | 'medium' | 'large';
  isLoading?: boolean;
  icon?: ReactNode;
  children: ReactNode;
}

const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'medium',
  isLoading = false,
  icon,
  disabled,
  className,
  children,
  onClick,
  type = 'button',
  ...rest
}) => {
  const [isActive, setIsActive] = useState(false);

  const handleClick = useCallback<React.MouseEventHandler<HTMLButtonElement>>(
    (event) => {
      if (!isLoading && !disabled) {
        setIsActive(true);
        onClick?.(event);
        setTimeout(() => setIsActive(false), 150);
      }
    },
    [isLoading, disabled, onClick]
  );

  const classNames = [
    styles.button,
    styles[variant],
    styles[size],
    isActive && styles.active,
    isLoading && styles.loading,
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      className={classNames}
      onClick={handleClick}
      aria-busy={isLoading}
      aria-disabled={disabled}
      {...rest}
    >
      {icon && <span className={styles.icon}>{icon}</span>}
      <span className={styles.label}>{children}</span>
      {isLoading && <span className={styles.spinner} aria-hidden="true" />}
    </button>
  );
};

export default Button;
```

### Step 3: Implement Custom Hooks for Reusable Logic
Extract complex logic into custom hooks:

```typescript
// useForm.ts
import { useState, useCallback } from 'react';

interface UseFormOptions<T> {
  initialValues: T;
  onSubmit: (values: T) => Promise<void> | void;
  validate?: (values: T) => Partial<Record<keyof T, string>>;
}

interface UseFormReturn<T> {
  values: T;
  errors: Partial<Record<keyof T, string>>;
  touched: Partial<Record<keyof T, boolean>>;
  isSubmitting: boolean;
  handleChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handleBlur: (e: React.FocusEvent<HTMLInputElement>) => void;
  handleSubmit: (e: React.FormEvent<HTMLFormElement>) => Promise<void>;
  reset: () => void;
}

export function useForm<T extends Record<string, any>>({
  initialValues,
  onSubmit,
  validate,
}: UseFormOptions<T>): UseFormReturn<T> {
  const [values, setValues] = useState<T>(initialValues);
  const [errors, setErrors] = useState<Partial<Record<keyof T, string>>>({});
  const [touched, setTouched] = useState<Partial<Record<keyof T, boolean>>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setValues((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  }, []);

  const handleBlur = useCallback((e: React.FocusEvent<HTMLInputElement>) => {
    const { name } = e.target;
    setTouched((prev) => ({ ...prev, [name]: true }));

    if (validate) {
      const newErrors = validate(values);
      setErrors(newErrors);
    }
  }, [values, validate]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent<HTMLFormElement>) => {
      e.preventDefault();

      if (validate) {
        const newErrors = validate(values);
        setErrors(newErrors);
        if (Object.keys(newErrors).length > 0) return;
      }

      setIsSubmitting(true);
      try {
        await onSubmit(values);
      } finally {
        setIsSubmitting(false);
      }
    },
    [values, validate, onSubmit]
  );

  const reset = useCallback(() => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
  }, [initialValues]);

  return {
    values,
    errors,
    touched,
    isSubmitting,
    handleChange,
    handleBlur,
    handleSubmit,
    reset,
  };
}
```

### Step 4: Add Error Boundary for Error Handling
Implement error boundaries for graceful degradation:

```typescript
interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div role="alert" style={{ padding: '20px', color: '#d32f2f' }}>
            <h2>Something went wrong</h2>
            <p>{this.state.error?.message}</p>
            <button onClick={() => window.location.reload()}>Reload page</button>
          </div>
        )
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
```

### Step 5: Implement Accessibility (ARIA)
Add comprehensive accessibility features:

```typescript
interface AccessibleSelectProps {
  options: Array<{ value: string; label: string }>;
  value: string;
  onChange: (value: string) => void;
  label: string;
  required?: boolean;
  error?: string;
  disabled?: boolean;
  placeholder?: string;
}

const AccessibleSelect: React.FC<AccessibleSelectProps> = ({
  options,
  value,
  onChange,
  label,
  required,
  error,
  disabled,
  placeholder,
}) => {
  const id = React.useId();
  const errorId = `${id}-error`;
  const describedById = error ? errorId : undefined;

  return (
    <div>
      <label htmlFor={id}>
        {label}
        {required && <span aria-label="required">*</span>}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        aria-required={required}
        aria-invalid={!!error}
        aria-describedby={describedById}
        className={error ? 'select-error' : ''}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {error && (
        <span id={errorId} role="alert" className="error-message">
          {error}
        </span>
      )}
    </div>
  );
};

export default AccessibleSelect;
```

### Step 6: Create Storybook Stories
Document components with interactive stories:

```typescript
// Button.stories.tsx
import { Meta, StoryObj } from '@storybook/react';
import Button from './Button';

const meta = {
  title: 'Components/Button',
  component: Button,
  tags: ['autodocs'],
  parameters: {
    layout: 'centered',
  },
  argTypes: {
    variant: {
      control: 'select',
      options: ['primary', 'secondary', 'danger'],
    },
    size: {
      control: 'select',
      options: ['small', 'medium', 'large'],
    },
    disabled: {
      control: 'boolean',
    },
    isLoading: {
      control: 'boolean',
    },
    children: {
      control: 'text',
    },
  },
} satisfies Meta<typeof Button>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Primary: Story = {
  args: {
    variant: 'primary',
    children: 'Click me',
  },
};

export const Secondary: Story = {
  args: {
    variant: 'secondary',
    children: 'Secondary Button',
  },
};

export const Loading: Story = {
  args: {
    variant: 'primary',
    isLoading: true,
    children: 'Saving...',
  },
};

export const Disabled: Story = {
  args: {
    variant: 'primary',
    disabled: true,
    children: 'Disabled Button',
  },
};

export const AllSizes: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '10px' }}>
      <Button size="small">Small</Button>
      <Button size="medium">Medium</Button>
      <Button size="large">Large</Button>
    </div>
  ),
};
```

### Step 7: Write Comprehensive Unit Tests
Test components with React Testing Library:

```typescript
// Button.test.tsx
import { render, screen, userEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import Button from './Button';

describe('Button', () => {
  it('renders with children', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick handler when clicked', async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Click me</Button>);

    await userEvent.click(screen.getByText('Click me'));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('applies correct variant class', () => {
    const { container } = render(<Button variant="danger">Delete</Button>);
    expect(container.firstChild).toHaveClass('danger');
  });

  it('disables button when loading', async () => {
    const onClick = vi.fn();
    render(
      <Button isLoading onClick={onClick}>
        Save
      </Button>
    );

    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('aria-busy', 'true');

    await userEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it('disables button when disabled prop is true', () => {
    render(<Button disabled>Disabled</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('has proper accessibility attributes', () => {
    render(<Button aria-label="Save changes">Save</Button>);
    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('aria-label', 'Save changes');
  });

  it('renders icon when provided', () => {
    render(
      <Button icon={<span data-testid="icon">📝</span>}>
        Edit
      </Button>
    );
    expect(screen.getByTestId('icon')).toBeInTheDocument();
  });
});
```

## Output Template

```typescript
interface {{ComponentName}}Props {{extends_interface}} {
  {{prop_definitions}}
}

const {{ComponentName}}: React.FC<{{ComponentName}}Props> = ({
  {{destructured_props}}
}) => {
  {{hooks_and_state}}
  {{event_handlers}}
  {{return_jsx}}
};

export default {{ComponentName}};

// {{ComponentName}}.stories.tsx
export const {{StoryName}}: Story = {
  args: {
    {{story_args}}
  },
};

// {{ComponentName}}.test.tsx
describe('{{ComponentName}}', () => {
  it('{{test_description}}', () => {
    {{test_implementation}}
  });
});
```

## Quality Gates
- [ ] Component has complete TypeScript interface for all props
- [ ] All props are documented with JSDoc comments
- [ ] Component uses React hooks (not class components)
- [ ] Event handlers use useCallback to prevent unnecessary re-renders
- [ ] All accessible elements have proper ARIA attributes (role, aria-label, aria-describedby)
- [ ] Component has at least 5 unit tests using React Testing Library
- [ ] Storybook stories cover all major variants and states
- [ ] Component handles loading and error states gracefully
- [ ] Component is responsive and works on mobile/tablet/desktop
- [ ] No console warnings or errors when component renders

## Examples

### Good Output (excerpt)
```typescript
interface CardProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  onClick?: () => void;
  loading?: boolean;
  error?: string;
}

const Card: React.FC<CardProps> = ({
  title,
  subtitle,
  children,
  onClick,
  loading,
  error,
}) => {
  const id = React.useId();
  const errorId = `${id}-error`;

  return (
    <article
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      aria-labelledby={`${id}-title`}
    >
      <h2 id={`${id}-title`}>{title}</h2>
      {subtitle && <p>{subtitle}</p>}
      {loading && <LoadingSpinner />}
      {error && <span id={errorId}>{error}</span>}
      {children}
    </article>
  );
};
```

### Bad Output (what to avoid)
```typescript
const Card = ({ data }) => {
  // No props interface
  // No accessibility
  // No loading/error handling
  return <div onClick={data.onClick}>{data.title}</div>;
};
```

## Common Mistakes

1. **Missing ARIA Labels on Interactive Elements**: Buttons without aria-label or accessible text confuse screen reader users. Solution: Every button/link needs accessible text: `<button aria-label="Close dialog">×</button>`.

2. **Not Using useCallback for Event Handlers**: Creates new function reference on every render, causing child components to re-render unnecessarily. Solution: Wrap event handlers in useCallback: `const handleChange = useCallback((e) => { ... }, [])`.

3. **Storing Props in useState**: Component receives updated prop but state keeps old value. Solution: Use the prop directly or useEffect to sync: `useEffect(() => setLocalValue(prop), [prop])`.

4. **Forgetting React.useId() for Accessibility**: Using hardcoded IDs in reusable components causes duplicate IDs when component renders multiple times. Breaks label associations. Solution: Use `const id = React.useId()` for dynamic unique IDs.

5. **Not Testing Error Boundaries**: Component crashes during render; entire application fails. Errors silently propagate to production. Solution: Wrap components in ErrorBoundary and test error states.

6. **Missing Controlled/Uncontrolled Pattern Documentation**: Input component sometimes controlled (value prop provided) and sometimes uncontrolled causes confusion. Solution: Clearly document: "This is a controlled component; value and onChange are required."

## Anti-Patterns

1. **Prop Drilling Through Multiple Layers**: Passing same props through 5 component levels is unmaintainable. Use Context API or state management instead of prop drilling.

2. **Inline Object/Function Props**: Passing `onClick={() => handler()}` or `style={{ color: 'red' }}` creates new references every render, breaking memoization. Move to component level.

3. **Mixing Controlled and Uncontrolled Elements**: Input component sometimes uses value prop and sometimes doesn't. React warns about switching between controlled/uncontrolled. Pick one pattern and stick to it.

4. **No Type Safety on Event Handlers**: Using `any` for event parameters prevents IDE autocomplete and allows bugs. Solution: Use proper React event types: `React.ChangeEvent<HTMLInputElement>`.

5. **Storybook Stories Without Testing**: Stories look good in Storybook but component breaks in real application with different props. Test actual usage patterns, not just happy paths.

6. **Accessibility as Afterthought**: Adding ARIA labels after component is built often misses semantic HTML. Solution: Write semantic HTML first (button for buttons, not divs), then add ARIA.
