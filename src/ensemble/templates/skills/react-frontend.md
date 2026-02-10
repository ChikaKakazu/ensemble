# React Frontend Skill

## 概要
React/Next.jsコンポーネント設計、hooks、状態管理の専門知識。

## コンポーネント設計原則

### コンポーネント分類
1. **Presentational Component**: 見た目のみ（props受け取り、表示）
2. **Container Component**: ロジック担当（状態管理、API呼び出し）
3. **Page Component**: ルーティング単位（Next.js）

### 単一責任の原則
- 1コンポーネント = 1つの責務
- 大きくなったら分割する

### Props設計
```tsx
interface ButtonProps {
  label: string;
  onClick: () => void;
  variant?: 'primary' | 'secondary';
  disabled?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  label,
  onClick,
  variant = 'primary',
  disabled = false
}) => {
  return (
    <button
      className={`btn btn-${variant}`}
      onClick={onClick}
      disabled={disabled}
    >
      {label}
    </button>
  );
};
```

## Hooks活用

### useState
```tsx
const [count, setCount] = useState(0);
```

### useEffect
```tsx
useEffect(() => {
  // 副作用（API呼び出し、購読など）
  fetchData();

  return () => {
    // クリーンアップ
  };
}, [dependency]); // 依存配列
```

### useCallback
```tsx
const memoizedCallback = useCallback(
  () => {
    doSomething(a, b);
  },
  [a, b], // 依存配列
);
```

### useMemo
```tsx
const expensiveValue = useMemo(
  () => computeExpensiveValue(a, b),
  [a, b]
);
```

### Custom Hooks
```tsx
function useFetch<T>(url: string) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    fetch(url)
      .then(res => res.json())
      .then(data => {
        setData(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err);
        setLoading(false);
      });
  }, [url]);

  return { data, loading, error };
}
```

## 状態管理

### ローカル状態（useState）
- コンポーネント内部のみで使う状態

### グローバル状態（Context API、Zustand、Recoil）
- 複数コンポーネントで共有する状態

### サーバー状態（React Query、SWR）
- APIから取得するデータ

```tsx
import { useQuery } from '@tanstack/react-query';

function Users() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: () => fetch('/api/users').then(res => res.json())
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return <ul>{data.map(user => <li key={user.id}>{user.name}</li>)}</ul>;
}
```

## パフォーマンス最適化

- **React.memo**: 不要な再レンダリング防止
- **useCallback/useMemo**: 関数・値のメモ化
- **Code Splitting**: React.lazy、動的import
- **仮想化**: 大量リストの表示（react-window）

## アクセシビリティ（a11y）

- **セマンティックHTML**: `<button>`, `<nav>`, `<main>`など
- **aria属性**: スクリーンリーダー対応
- **キーボード操作**: Tabキー、Enterキーで操作可能に

## テスト

- **Unit Test**: React Testing Library
- **E2E Test**: Playwright、Cypress
- **Visual Regression Test**: Storybook + Chromatic
