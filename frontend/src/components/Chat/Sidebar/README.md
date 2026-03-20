# ChatSidebar Component

A responsive, accessible sidebar component for displaying and managing chat groups.

## Features

- **Searchable Group List**: Real-time search filtering with keyword highlighting
- **Responsive Design**: Adapts to mobile (drawer), tablet (fixed), and desktop (resizable) layouts
- **Keyboard Navigation**: Full keyboard support with arrow keys
- **Accessibility**: WCAG compliant with proper ARIA labels and roles
- **Performance Optimized**: React.memo for list items, efficient re-renders
- **Unread Badges**: Visual indicators for unread message counts
- **Time Formatting**: Smart relative time display (刚刚, 5分钟前, etc.)

## Components

### ChatSidebar

Main sidebar container with search and group list.

**Props:**
```typescript
interface ChatSidebarProps {
  groups: GroupInfo[];           // Array of group data
  selectedGroupId?: string;      // Currently selected group ID
  onSelectGroup: (groupId: string) => void;  // Selection handler
  onSearch?: (keyword: string) => void;      // Search handler
  className?: string;            // Additional CSS classes
}
```

### GroupListItem

Individual group list item with avatar, name, and preview.

**Props:**
```typescript
interface GroupListItemProps {
  group: GroupInfo;              // Group data
  isSelected?: boolean;          // Selection state
  onClick?: () => void;          // Click handler
  className?: string;            // Additional CSS classes
}
```

### GroupInfo

Data structure for group information.

```typescript
interface GroupInfo {
  id: string;                    // Unique group identifier
  name: string;                  // Group display name
  avatar?: string;               // Avatar image URL (optional)
  lastMessage?: string;          // Last message preview (optional)
  lastMessageTime?: Date;        // Last message timestamp (optional)
  unreadCount?: number;          // Unread message count (optional)
}
```

## Usage

### Basic Example

```tsx
import { ChatSidebar } from './components/Chat/Sidebar';

function MyChat() {
  const [selectedId, setSelectedId] = useState('1');

  const groups = [
    {
      id: '1',
      name: 'React Developers',
      lastMessage: 'Check out the new hooks!',
      lastMessageTime: new Date(),
      unreadCount: 3
    }
  ];

  return (
    <ChatSidebar
      groups={groups}
      selectedGroupId={selectedId}
      onSelectGroup={setSelectedId}
      onSearch={(keyword) => console.log(keyword)}
    />
  );
}
```

### Integration with Existing ChatInterface

```tsx
import { ChatSidebar } from './components/Chat/Sidebar';
import { TelegramGroup } from './types';

// Convert TelegramGroup to GroupInfo
const convertToGroupInfo = (group: TelegramGroup) => ({
  id: group.id.toString(),
  name: group.title,
  avatar: group.avatar_url,
  lastMessage: group.last_message?.text,
  lastMessageTime: group.last_message?.date
    ? new Date(group.last_message.date)
    : undefined,
  unreadCount: group.unread_count
});

// In your component
<ChatSidebar
  groups={telegramGroups.map(convertToGroupInfo)}
  selectedGroupId={selectedGroup?.id.toString()}
  onSelectGroup={(id) => {
    const group = telegramGroups.find(g => g.id.toString() === id);
    if (group) selectGroup(group);
  }}
/>
```

## Responsive Behavior

### Mobile (≤768px)
- **Layout**: Drawer mode
- **Width**: 85% of screen (max 400px)
- **Behavior**: Overlay on top of content
- **Shadow**: Enhanced for depth perception

### Tablet (769px - 1024px)
- **Layout**: Fixed sidebar
- **Width**: 280px
- **Behavior**: Always visible, non-resizable

### Desktop (≥1025px)
- **Layout**: Resizable sidebar
- **Width**: 320px (default)
- **Range**: 260px - 420px
- **Behavior**: User can resize horizontally

## Keyboard Navigation

- **Arrow Down**: Select next group
- **Arrow Up**: Select previous group
- **Enter/Space**: Activate selected group
- **Tab**: Navigate through interactive elements

## Accessibility Features

- Semantic HTML with proper roles (`navigation`, `list`, `listitem`)
- ARIA labels for screen readers
- Keyboard navigation support
- Focus indicators for keyboard users
- High contrast mode support
- Reduced motion support

## Performance Considerations

1. **React.memo**: GroupListItem is memoized to prevent unnecessary re-renders
2. **useCallback**: Event handlers are memoized
3. **useMemo**: Filtered groups list is memoized
4. **Virtual Scrolling**: Consider adding react-window for 100+ groups

## Styling

The component uses CSS Modules for scoped styling. Key design tokens:

```css
/* Colors */
--background: #ffffff
--border: rgba(0, 0, 0, 0.06)
--selected-bg: #f0f5ff
--hover-bg: #fafafa

/* Dimensions */
--item-height: 72px
--mobile-width: 85%
--tablet-width: 280px
--desktop-width: 320px
```

## Browser Support

- Chrome/Edge: Latest 2 versions
- Firefox: Latest 2 versions
- Safari: Latest 2 versions
- Mobile browsers: iOS Safari 12+, Chrome Android

## Testing

### Unit Tests
```bash
npm test -- ChatSidebar
```

### Manual Testing Checklist
- [ ] Search filters groups correctly
- [ ] Selected state highlights properly
- [ ] Keyboard navigation works
- [ ] Responsive layouts adapt correctly
- [ ] Unread badges display
- [ ] Long text truncates properly
- [ ] Empty state shows when no groups

## Future Enhancements

- [ ] Virtual scrolling for large lists (react-window)
- [ ] Drag-to-reorder groups
- [ ] Context menu for group actions
- [ ] Group categories/folders
- [ ] Pin/unpin groups
- [ ] Swipe gestures on mobile

## Files

```
frontend/src/components/Chat/Sidebar/
├── ChatSidebar.tsx              # Main sidebar component (120 lines)
├── ChatSidebar.module.css       # Sidebar styles (150 lines)
├── GroupListItem.tsx            # List item component (95 lines)
├── GroupListItem.module.css     # List item styles (130 lines)
├── index.ts                     # Exports
├── ChatSidebar.example.tsx      # Usage examples
└── README.md                    # This file
```

## License

Part of TgGod project - Telegram Group Download System
