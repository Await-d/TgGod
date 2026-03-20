# ChatHeader Component

Modern, responsive chat interface header component for TgGod.

## Files Created

- `/home/await/project/TgGod/frontend/src/components/Chat/Header/ChatHeader.tsx` (140 lines)
- `/home/await/project/TgGod/frontend/src/components/Chat/Header/ChatHeader.module.css` (184 lines)
- `/home/await/project/TgGod/frontend/src/components/Chat/Header/index.ts`

## Features

### Core Functionality
- **Group Information Display**
  - Group avatar with gradient background
  - Group name with text truncation
  - Member count and online status
  - Online status badge indicator

- **Action Buttons**
  - Sidebar toggle (mobile only)
  - Search messages
  - More options dropdown menu

- **Responsive Design**
  - Desktop (≥1025px): Full layout, 64px height
  - Tablet (769-1024px): Medium layout, 60px height
  - Mobile (≤768px): Compact layout, 56px height, hidden member count
  - Small mobile (≤480px): Extra compact with reduced padding

### Design Specifications

**Visual Design:**
- Background: `linear-gradient(180deg, #ffffff 0%, #fafbfc 100%)`
- Border: Bottom 1px `rgba(0, 0, 0, 0.06)`
- Shadow: `0 1px 3px rgba(0, 0, 0, 0.02)`
- Avatar gradient: `linear-gradient(135deg, #667eea 0%, #764ba2 100%)`
- Font: SF Pro Display / Segoe UI / System fonts

**Interactions:**
- Smooth transitions (250ms cubic-bezier)
- Hover effects on buttons
- Focus-visible outlines for accessibility
- Touch-friendly targets on mobile (44px minimum)

**Dark Mode:**
- Automatic dark mode support via `prefers-color-scheme`
- Adjusted colors and shadows for dark backgrounds

## Usage

### Basic Example
```tsx
import ChatHeader from '@/components/Chat/Header';

function ChatInterface() {
  return (
    <ChatHeader
      groupName="Tech Discussion"
      memberCount={1234}
      onlineCount={89}
    />
  );
}
```

### With All Props
```tsx
import ChatHeader from '@/components/Chat/Header';
import { useState } from 'react';

function ChatInterface() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);

  return (
    <ChatHeader
      groupName="Tech Discussion"
      groupAvatar="/avatars/tech-group.jpg"
      memberCount={1234}
      onlineCount={89}
      onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      onSearch={() => setSearchOpen(true)}
      showSidebarToggle={true}
      className="custom-header"
    />
  );
}
```

### Responsive Usage
```tsx
import ChatHeader from '@/components/Chat/Header';
import { useResponsiveLayout } from '@/hooks/useResponsiveLayout';

function ChatInterface() {
  const { isMobile } = useResponsiveLayout();

  return (
    <ChatHeader
      groupName="Tech Discussion"
      memberCount={1234}
      onlineCount={89}
      showSidebarToggle={isMobile}
      onToggleSidebar={() => console.log('Toggle sidebar')}
    />
  );
}
```

## Props Interface

```typescript
interface ChatHeaderProps {
  /** Group name to display (required) */
  groupName: string;

  /** Optional group avatar URL */
  groupAvatar?: string;

  /** Total member count */
  memberCount?: number;

  /** Online member count */
  onlineCount?: number;

  /** Callback when sidebar toggle is clicked */
  onToggleSidebar?: () => void;

  /** Callback when search is clicked */
  onSearch?: () => void;

  /** Show sidebar toggle button (typically for mobile) */
  showSidebarToggle?: boolean;

  /** Additional CSS class */
  className?: string;
}
```

## Performance Optimizations

1. **React.memo**: Component is memoized to prevent unnecessary re-renders
2. **useMemo**: Expensive computations cached (menu items, member count text, avatar fallback)
3. **useCallback**: Event handlers memoized to maintain referential equality
4. **CSS Modules**: Scoped styles with minimal specificity
5. **Responsive Hook**: Debounced resize handling (150ms)

## Accessibility Features

- **ARIA Labels**: All interactive elements have descriptive labels
- **Semantic HTML**: Proper use of `<header>`, `<h1>`, `<button>` tags
- **Keyboard Navigation**: Full keyboard support for all actions
- **Focus Indicators**: Visible focus outlines for keyboard users
- **Screen Reader Support**: Proper role and aria-label attributes
- **Reduced Motion**: Respects `prefers-reduced-motion` setting
- **High Contrast**: Enhanced borders and colors for high contrast mode

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

## Dependencies

- React 18+
- Ant Design 5.x
- @ant-design/icons
- Custom hooks: `useResponsiveLayout`

## Testing Checklist

- [x] Component renders without errors
- [x] Props are correctly typed
- [x] Responsive breakpoints work correctly
- [x] Dark mode styles apply properly
- [x] Accessibility features functional
- [x] Performance optimizations in place
- [x] Code under 150 lines
- [x] CSS under 200 lines
- [x] No TypeScript errors

## Future Enhancements

- [ ] Add group info modal on avatar click
- [ ] Implement notification badge on bell icon
- [ ] Add typing indicator
- [ ] Support for group verification badge
- [ ] Customizable theme colors
- [ ] Animation on member count changes

## Notes

- The component uses CSS Modules for styling isolation
- All callbacks are optional and have default no-op behavior
- The component is fully controlled - parent manages state
- Member count is hidden on mobile to save space
- Touch targets are 44px minimum on mobile for accessibility
