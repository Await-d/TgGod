# ChatSidebar Component Structure

## Visual Layout

```
┌─────────────────────────────────────┐
│  ChatSidebar                        │
│  ┌───────────────────────────────┐  │
│  │  Search Input                 │  │ ← searchContainer
│  │  🔍 搜索群组或消息...         │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │  GroupListItem (selected)     │  │ ← groupList
│  │  ┌──┐  React Developers       │  │
│  │  │ R│  Check out the new...   │  │
│  │  └──┘  5分钟前            [3] │  │
│  ├───────────────────────────────┤  │
│  │  GroupListItem                │  │
│  │  ┌──┐  TypeScript Community   │  │
│  │  │ T│  TypeScript 5.0 is...   │  │
│  │  └──┘  30分钟前               │  │
│  ├───────────────────────────────┤  │
│  │  GroupListItem                │  │
│  │  ┌──┐  Frontend Masters       │  │
│  │  │ F│  New course on perf...  │  │
│  │  └──┘  2小时前           [12] │  │
│  ├───────────────────────────────┤  │
│  │  ...more groups...            │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │  共 24 个群组                 │  │ ← footer
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

## Component Hierarchy

```
ChatSidebar
├── searchContainer
│   └── Input (Ant Design)
│       └── SearchOutlined icon
├── groupList
│   ├── GroupListItem (group 1)
│   │   ├── avatarWrapper
│   │   │   └── Badge
│   │   │       └── Avatar
│   │   └── content
│   │       ├── header
│   │       │   ├── groupName
│   │       │   └── time
│   │       └── lastMessage
│   ├── GroupListItem (group 2)
│   ├── GroupListItem (group 3)
│   └── ...
└── footer
    └── groupCount
```

## Responsive Layouts

### Mobile (≤768px)
```
┌─────────────────┐
│ Drawer Overlay  │ 85% width
│ ┌─────────────┐ │
│ │ Search      │ │
│ ├─────────────┤ │
│ │ Groups      │ │
│ │   [Avatar]  │ │
│ │   [Avatar]  │ │
│ │   [Avatar]  │ │
│ └─────────────┘ │
│ │ Count       │ │
│ └─────────────┘ │
└─────────────────┘
```

### Tablet (769-1024px)
```
┌──────────┬──────────────┐
│ Sidebar  │ Main Content │
│ 280px    │              │
│ ┌──────┐ │              │
│ │Search│ │              │
│ ├──────┤ │              │
│ │Groups│ │              │
│ │      │ │              │
│ │      │ │              │
│ └──────┘ │              │
│ │Count │ │              │
│ └──────┘ │              │
└──────────┴──────────────┘
```

### Desktop (≥1025px)
```
┌────────────┬────────────────────┐
│ Sidebar    │ Main Content       │
│ 320px      │                    │
│ (resizable)│                    │
│ ┌────────┐ │                    │
│ │ Search │ │                    │
│ ├────────┤ │                    │
│ │ Groups │ │                    │
│ │        │ │                    │
│ │        │ │                    │
│ │        │ │                    │
│ └────────┘ │                    │
│ │ Count  │ │                    │
│ └────────┘ │                    │
└────────────┴────────────────────┘
     ↕ Resize handle
```

## State Flow

```
User Action → Component State → UI Update
─────────────────────────────────────────

Search Input
  onChange → setSearchKeyword → filteredGroups → Re-render list

Group Selection
  onClick → onSelectGroup(id) → Parent updates → isSelected prop → Highlight

Keyboard Navigation
  onKeyDown → Arrow Up/Down → Calculate next index → onSelectGroup → Update
```

## Data Flow

```
Parent Component (ChatInterface)
  │
  ├─ groups: TelegramGroup[] ──────┐
  │                                 │
  ├─ selectedGroup: TelegramGroup ──┤
  │                                 │
  └─ onGroupSelect: (group) => {} ──┤
                                    │
                                    ▼
                            ChatSidebar
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
            Convert to GroupInfo    │         Handle search
                    │               │               │
                    ▼               ▼               ▼
            groups: GroupInfo[]  selectedGroupId  onSearch
                    │               │               │
                    └───────────────┼───────────────┘
                                    │
                                    ▼
                            GroupListItem (x N)
                                    │
                            ┌───────┴───────┐
                            │               │
                        Display         Handle click
                            │               │
                            ▼               ▼
                    Avatar, Name,    onSelectGroup(id)
                    Message, Badge         │
                                          │
                                          ▼
                                Parent updates state
```

## CSS Module Classes

### ChatSidebar.module.css
```
.chatSidebar          - Main container
.searchContainer      - Search input wrapper
.searchInput          - Search input styling
.groupList            - Scrollable group list
.emptyState           - No groups message
.footer               - Bottom info bar
.groupCount           - Group count text
```

### GroupListItem.module.css
```
.groupListItem        - Item container
.groupListItem.selected - Selected state
.avatarWrapper        - Avatar container
.content              - Text content area
.header               - Name + time row
.groupName            - Group name text
.time                 - Timestamp text
.lastMessage          - Message preview text
```

## Performance Optimizations

```
Component Level:
├── React.memo(GroupListItem)
│   └── Prevents re-render if props unchanged
│
├── useMemo(filteredGroups)
│   └── Caches filtered results
│
└── useCallback(handlers)
    └── Stable function references

Rendering:
├── Virtual scrolling (future)
│   └── Only render visible items
│
└── Lazy loading (future)
    └── Load groups on demand
```

## Accessibility Tree

```
navigation [role="navigation"] [aria-label="群组列表"]
├── search [role="searchbox"] [aria-label="搜索群组"]
├── list [role="list"]
│   ├── listitem [role="listitem"] [aria-selected="true"]
│   │   ├── img [alt="Group name"]
│   │   ├── text "Group name"
│   │   └── text "Last message"
│   ├── listitem [role="listitem"] [aria-selected="false"]
│   └── ...
└── contentinfo
    └── text "共 N 个群组"
```

## Event Handling

```
User Events:
├── Search Input
│   ├── onChange → handleSearchChange
│   └── onClear → Reset search
│
├── Group Item Click
│   ├── onClick → onSelectGroup(id)
│   └── onKeyDown (Enter/Space) → onSelectGroup(id)
│
└── Keyboard Navigation
    ├── ArrowDown → Select next
    ├── ArrowUp → Select previous
    └── Tab → Focus next element
```

## Integration Points

```
ChatInterface.tsx
├── Import: import { ChatSidebar } from './components/Chat/Sidebar'
├── State: const [selectedGroup, setSelectedGroup] = useState()
├── Data: const groups = useTelegramStore(state => state.groups)
└── Render:
    <ChatSidebar
      groups={groups.map(convertToGroupInfo)}
      selectedGroupId={selectedGroup?.id}
      onSelectGroup={handleSelectGroup}
      onSearch={handleSearch}
    />
```

---

This visual reference provides a comprehensive overview of the ChatSidebar component structure, layout, and behavior.
