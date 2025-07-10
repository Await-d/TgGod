import { renderHook, act } from '@testing-library/react';
import { useMobileGestures, useIsMobile, useKeyboardHeight } from '../useMobileGestures';

// Mock window properties
const mockWindowProperties = (properties: Record<string, any>) => {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: properties.innerWidth || 1024,
  });
  
  Object.defineProperty(window, 'innerHeight', {
    writable: true,
    configurable: true,
    value: properties.innerHeight || 768,
  });
  
  if (properties.userAgent) {
    Object.defineProperty(navigator, 'userAgent', {
      writable: true,
      configurable: true,
      value: properties.userAgent,
    });
  }
};

describe('useMobileGestures', () => {
  beforeEach(() => {
    // Reset window properties
    mockWindowProperties({ innerWidth: 1024, innerHeight: 768 });
  });

  test('should detect mobile device by screen width', () => {
    mockWindowProperties({ innerWidth: 360 });
    
    const { result } = renderHook(() => useIsMobile());
    
    expect(result.current).toBe(true);
  });

  test('should detect desktop device by screen width', () => {
    mockWindowProperties({ innerWidth: 1200 });
    
    const { result } = renderHook(() => useIsMobile());
    
    expect(result.current).toBe(false);
  });

  test('should detect mobile device by user agent', () => {
    mockWindowProperties({ 
      innerWidth: 1200,
      userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X)'
    });
    
    const { result } = renderHook(() => useIsMobile());
    
    expect(result.current).toBe(true);
  });

  test('should handle window resize', () => {
    const { result } = renderHook(() => useIsMobile());
    
    expect(result.current).toBe(false);
    
    act(() => {
      mockWindowProperties({ innerWidth: 400 });
      window.dispatchEvent(new Event('resize'));
    });
    
    expect(result.current).toBe(true);
  });
});

describe('useKeyboardHeight', () => {
  test('should detect keyboard visibility', () => {
    const { result } = renderHook(() => useKeyboardHeight());
    
    expect(result.current.isKeyboardVisible).toBe(false);
    expect(result.current.keyboardHeight).toBe(0);
  });
});

describe('Mobile gesture detection', () => {
  let mockElement: HTMLElement;
  
  beforeEach(() => {
    mockElement = document.createElement('div');
    document.body.appendChild(mockElement);
  });
  
  afterEach(() => {
    document.body.removeChild(mockElement);
  });

  test('should initialize without errors', () => {
    const mockSwipeLeft = jest.fn();
    const mockSwipeRight = jest.fn();
    
    const { result } = renderHook(() =>
      useMobileGestures({
        onSwipeLeft: mockSwipeLeft,
        onSwipeRight: mockSwipeRight,
        element: mockElement,
      })
    );
    
    expect(result.current.isSwiping).toBe(false);
  });

  test('should handle touch events', () => {
    const mockSwipeLeft = jest.fn();
    
    renderHook(() =>
      useMobileGestures({
        onSwipeLeft: mockSwipeLeft,
        threshold: 50,
        element: mockElement,
      })
    );

    // Simulate touch start
    const touchStart = new TouchEvent('touchstart', {
      touches: [{ clientX: 100, clientY: 100 } as Touch],
    });
    mockElement.dispatchEvent(touchStart);

    // Simulate touch end (swipe left)
    const touchEnd = new TouchEvent('touchend', {
      changedTouches: [{ clientX: 40, clientY: 100 } as Touch],
    });
    mockElement.dispatchEvent(touchEnd);

    expect(mockSwipeLeft).toHaveBeenCalled();
  });
});