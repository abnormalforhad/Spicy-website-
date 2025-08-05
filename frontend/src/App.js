import React, { useState, useEffect, createContext, useContext } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from "react-router-dom";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Cart Context
const CartContext = createContext();

const CartProvider = ({ children }) => {
  const [cartItems, setCartItems] = useState([]);
  const [cartOpen, setCartOpen] = useState(false);

  const addToCart = (product, quantity = 1) => {
    setCartItems(prev => {
      const existing = prev.find(item => item.product_id === product.id);
      if (existing) {
        return prev.map(item =>
          item.product_id === product.id
            ? { ...item, quantity: item.quantity + quantity }
            : item
        );
      }
      return [...prev, {
        product_id: product.id,
        product_name: product.name,
        product_image: product.image_url,
        quantity,
        price: product.price
      }];
    });
  };

  const removeFromCart = (productId) => {
    setCartItems(prev => prev.filter(item => item.product_id !== productId));
  };

  const updateQuantity = (productId, quantity) => {
    if (quantity <= 0) {
      removeFromCart(productId);
      return;
    }
    setCartItems(prev =>
      prev.map(item =>
        item.product_id === productId ? { ...item, quantity } : item
      )
    );
  };

  const clearCart = () => {
    setCartItems([]);
  };

  const getTotalItems = () => {
    return cartItems.reduce((total, item) => total + item.quantity, 0);
  };

  const getTotalPrice = () => {
    return cartItems.reduce((total, item) => total + (item.price * item.quantity), 0);
  };

  return (
    <CartContext.Provider value={{
      cartItems,
      addToCart,
      removeFromCart,
      updateQuantity,
      clearCart,
      getTotalItems,
      getTotalPrice,
      cartOpen,
      setCartOpen
    }}>
      {children}
    </CartContext.Provider>
  );
};

const useCart = () => {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within CartProvider');
  }
  return context;
};

// Header Component
const Header = () => {
  const { getTotalItems, setCartOpen } = useCart();
  const navigate = useNavigate();

  return (
    <header className="bg-white shadow-lg fixed w-full top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center cursor-pointer" onClick={() => navigate('/')}>
            <h1 className="text-2xl font-bold text-orange-600">SpiceBazaar</h1>
          </div>
          
          <nav className="hidden md:flex space-x-8">
            <button onClick={() => navigate('/')} className="text-gray-700 hover:text-orange-600 transition duration-300">Home</button>
            <button onClick={() => navigate('/products')} className="text-gray-700 hover:text-orange-600 transition duration-300">Products</button>
            <button onClick={() => navigate('/about')} className="text-gray-700 hover:text-orange-600 transition duration-300">About</button>
          </nav>
          
          <div className="flex items-center space-x-4">
            <button 
              onClick={() => setCartOpen(true)}
              className="relative p-2 text-gray-700 hover:text-orange-600 transition duration-300"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293A1 1 0 005 16v0a1 1 0 001 1h11M16 21a2 2 0 100-4 2 2 0 000 4zM9 21a2 2 0 100-4 2 2 0 000 4z" />
              </svg>
              {getTotalItems() > 0 && (
                <span className="absolute -top-1 -right-1 bg-orange-600 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                  {getTotalItems()}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

// Cart Sidebar
const CartSidebar = () => {
  const { cartItems, cartOpen, setCartOpen, removeFromCart, updateQuantity, getTotalPrice, clearCart } = useCart();
  const [customerEmail, setCustomerEmail] = useState('');
  const [isCheckingOut, setIsCheckingOut] = useState(false);

  const handleCheckout = async () => {
    if (!customerEmail || cartItems.length === 0) return;
    
    setIsCheckingOut(true);
    try {
      const checkoutItems = cartItems.map(item => ({
        product_id: item.product_id,
        quantity: item.quantity,
        price: item.price
      }));

      const response = await axios.post(`${API}/checkout/session`, {
        items: checkoutItems,
        customer_email: customerEmail,
        origin_url: window.location.origin
      });

      if (response.data.url) {
        window.location.href = response.data.url;
      }
    } catch (error) {
      console.error('Checkout failed:', error);
      alert('Checkout failed. Please try again.');
    } finally {
      setIsCheckingOut(false);
    }
  };

  if (!cartOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      <div className="absolute inset-0 bg-black bg-opacity-50" onClick={() => setCartOpen(false)}></div>
      <div className="absolute right-0 top-0 h-full w-96 bg-white shadow-xl overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold">Shopping Cart</h2>
            <button onClick={() => setCartOpen(false)} className="text-gray-500 hover:text-gray-700">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {cartItems.length === 0 ? (
            <p className="text-gray-500 text-center py-8">Your cart is empty</p>
          ) : (
            <>
              <div className="space-y-4 mb-6">
                {cartItems.map((item) => (
                  <div key={item.product_id} className="flex items-center space-x-4 p-4 border rounded-lg">
                    <img src={item.product_image} alt={item.product_name} className="w-16 h-16 object-cover rounded" />
                    <div className="flex-1">
                      <h3 className="font-semibold text-sm">{item.product_name}</h3>
                      <p className="text-orange-600 font-bold">${item.price}</p>
                      <div className="flex items-center space-x-2 mt-2">
                        <button
                          onClick={() => updateQuantity(item.product_id, item.quantity - 1)}
                          className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center hover:bg-gray-300"
                        >
                          -
                        </button>
                        <span className="w-8 text-center">{item.quantity}</span>
                        <button
                          onClick={() => updateQuantity(item.product_id, item.quantity + 1)}
                          className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center hover:bg-gray-300"
                        >
                          +
                        </button>
                        <button
                          onClick={() => removeFromCart(item.product_id)}
                          className="text-red-500 hover:text-red-700 ml-2"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="border-t pt-4">
                <div className="flex justify-between items-center mb-4">
                  <span className="font-bold text-lg">Total: ${getTotalPrice().toFixed(2)}</span>
                </div>
                
                <input
                  type="email"
                  placeholder="Enter your email"
                  value={customerEmail}
                  onChange={(e) => setCustomerEmail(e.target.value)}
                  className="w-full p-3 border rounded-lg mb-4 focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                />
                
                <button
                  onClick={handleCheckout}
                  disabled={!customerEmail || cartItems.length === 0 || isCheckingOut}
                  className="w-full bg-orange-600 text-white py-3 rounded-lg hover:bg-orange-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-semibold"
                >
                  {isCheckingOut ? 'Processing...' : 'Checkout'}
                </button>
                
                <button
                  onClick={clearCart}
                  className="w-full mt-2 text-gray-500 hover:text-gray-700 py-2"
                >
                  Clear Cart
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

// Home Page
const Home = () => {
  const [featuredProducts, setFeaturedProducts] = useState([]);
  const { addToCart } = useCart();

  useEffect(() => {
    const fetchFeaturedProducts = async () => {
      try {
        const response = await axios.get(`${API}/products/featured`);
        setFeaturedProducts(response.data);
      } catch (error) {
        console.error('Failed to fetch featured products:', error);
      }
    };

    fetchFeaturedProducts();
  }, []);

  return (
    <div className="pt-16">
      {/* Hero Section */}
      <section 
        className="relative h-96 bg-cover bg-center flex items-center justify-center"
        style={{
          backgroundImage: 'linear-gradient(rgba(0,0,0,0.4), rgba(0,0,0,0.4)), url(https://images.unsplash.com/photo-1613216514014-edb92d8e3e8d?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzh8MHwxfHNlYXJjaHwzfHx0dXJtZXJpYyUyMHBvd2RlcnxlbnwwfHx8b3JhbmdlfDE3NTQzODM5NDZ8MA&ixlib=rb-4.1.0&q=85)'
        }}
      >
        <div className="text-center text-white">
          <h1 className="text-5xl font-bold mb-4">Premium Quality Spices</h1>
          <p className="text-xl mb-8">Authentic flavors from around the world</p>
          <button className="bg-orange-600 text-white px-8 py-3 rounded-lg text-lg hover:bg-orange-700 transition duration-300">
            Shop Now
          </button>
        </div>
      </section>

      {/* Featured Products */}
      <section className="py-16 px-4">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12">Featured Products</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {featuredProducts.map((product) => (
              <div key={product.id} className="bg-white rounded-lg shadow-lg overflow-hidden hover:shadow-xl transition duration-300">
                <img src={product.image_url} alt={product.name} className="w-full h-48 object-cover" />
                <div className="p-6">
                  <h3 className="text-xl font-bold mb-2">{product.name}</h3>
                  <p className="text-gray-600 mb-4">{product.description}</p>
                  <div className="flex justify-between items-center mb-4">
                    <span className="text-2xl font-bold text-orange-600">${product.price}</span>
                    <span className="text-sm text-gray-500">{product.weight}</span>
                  </div>
                  <button
                    onClick={() => addToCart(product)}
                    className="w-full bg-orange-600 text-white py-2 rounded-lg hover:bg-orange-700 transition duration-300"
                  >
                    Add to Cart
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};

// Products Page
const Products = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const { addToCart } = useCart();

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        const response = await axios.get(`${API}/products`);
        setProducts(response.data);
      } catch (error) {
        console.error('Failed to fetch products:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchProducts();
  }, []);

  if (loading) {
    return (
      <div className="pt-16 min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading products...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="pt-16">
      <section className="py-16 px-4">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-4xl font-bold text-center mb-12">All Products</h1>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
            {products.map((product) => (
              <div key={product.id} className="bg-white rounded-lg shadow-lg overflow-hidden hover:shadow-xl transition duration-300">
                <img src={product.image_url} alt={product.name} className="w-full h-48 object-cover" />
                <div className="p-6">
                  <h3 className="text-xl font-bold mb-2">{product.name}</h3>
                  <p className="text-gray-600 mb-4 text-sm">{product.description}</p>
                  <div className="flex justify-between items-center mb-4">
                    <span className="text-xl font-bold text-orange-600">${product.price}</span>
                    <span className="text-sm text-gray-500">{product.weight}</span>
                  </div>
                  <div className="mb-3">
                    <span className="inline-block bg-orange-100 text-orange-800 text-xs px-2 py-1 rounded-full">
                      {product.category}
                    </span>
                  </div>
                  <button
                    onClick={() => addToCart(product)}
                    className="w-full bg-orange-600 text-white py-2 rounded-lg hover:bg-orange-700 transition duration-300"
                  >
                    Add to Cart
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};

// Checkout Success Page
const CheckoutSuccess = () => {
  const [paymentStatus, setPaymentStatus] = useState('checking');
  const [sessionId, setSessionId] = useState(null);
  const location = useLocation();

  useEffect(() => {
    const urlParams = new URLSearchParams(location.search);
    const sessionIdParam = urlParams.get('session_id');
    
    if (sessionIdParam) {
      setSessionId(sessionIdParam);
      pollPaymentStatus(sessionIdParam);
    }
  }, [location]);

  const pollPaymentStatus = async (sessionId, attempts = 0) => {
    const maxAttempts = 5;
    const pollInterval = 2000; // 2 seconds

    if (attempts >= maxAttempts) {
      setPaymentStatus('timeout');
      return;
    }

    try {
      const response = await axios.get(`${API}/checkout/status/${sessionId}`);
      
      if (response.data.payment_status === 'paid') {
        setPaymentStatus('success');
        return;
      } else if (response.data.status === 'expired') {
        setPaymentStatus('expired');
        return;
      }

      // If payment is still pending, continue polling
      setTimeout(() => pollPaymentStatus(sessionId, attempts + 1), pollInterval);
    } catch (error) {
      console.error('Error checking payment status:', error);
      setPaymentStatus('error');
    }
  };

  return (
    <div className="pt-16 min-h-screen flex items-center justify-center">
      <div className="max-w-md mx-auto text-center p-8">
        {paymentStatus === 'checking' && (
          <>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto mb-4"></div>
            <h2 className="text-2xl font-bold mb-4">Processing Payment...</h2>
            <p className="text-gray-600">Please wait while we confirm your payment.</p>
          </>
        )}
        
        {paymentStatus === 'success' && (
          <>
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold mb-4 text-green-600">Payment Successful!</h2>
            <p className="text-gray-600 mb-6">Thank you for your purchase. Your spices are on their way!</p>
            <button 
              onClick={() => window.location.href = '/'}
              className="bg-orange-600 text-white px-6 py-3 rounded-lg hover:bg-orange-700 transition duration-300"
            >
              Continue Shopping
            </button>
          </>
        )}
        
        {paymentStatus === 'error' && (
          <>
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold mb-4 text-red-600">Payment Error</h2>
            <p className="text-gray-600 mb-6">There was an error processing your payment. Please try again.</p>
            <button 
              onClick={() => window.location.href = '/'}
              className="bg-orange-600 text-white px-6 py-3 rounded-lg hover:bg-orange-700 transition duration-300"
            >
              Back to Shop
            </button>
          </>
        )}
      </div>
    </div>
  );
};

// About Page
const About = () => {
  return (
    <div className="pt-16">
      <section className="py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl font-bold text-center mb-12">About SpiceBazaar</h1>
          <div className="prose prose-lg mx-auto">
            <p className="text-lg text-gray-600 mb-6">
              Welcome to SpiceBazaar, your premier destination for authentic, high-quality spices from around the world. 
              We specialize in bringing you the finest chili powder, turmeric powder, and exotic spice blends that will 
              transform your cooking experience.
            </p>
            <p className="text-lg text-gray-600 mb-6">
              Our spices are sourced directly from trusted farmers and suppliers who share our commitment to quality and sustainability. 
              Each product is carefully selected, processed, and packaged to preserve its natural flavor, aroma, and nutritional benefits.
            </p>
            <div className="grid md:grid-cols-2 gap-8 mt-12">
              <div>
                <h3 className="text-xl font-bold mb-4">Our Mission</h3>
                <p className="text-gray-600">
                  To bring authentic flavors to your kitchen while supporting sustainable farming practices and fair trade.
                </p>
              </div>
              <div>
                <h3 className="text-xl font-bold mb-4">Quality Promise</h3>
                <p className="text-gray-600">
                  Every spice is tested for purity and quality. We guarantee freshness and authenticity in every package.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

// Main App Component
function App() {
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    const initializeApp = async () => {
      try {
        // Initialize sample products
        await axios.post(`${API}/init-products`);
        setInitialized(true);
      } catch (error) {
        console.error('Failed to initialize app:', error);
        setInitialized(true); // Continue even if init fails
      }
    };

    initializeApp();
  }, []);

  if (!initialized) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Initializing SpiceBazaar...</p>
        </div>
      </div>
    );
  }

  return (
    <CartProvider>
      <div className="App min-h-screen bg-gray-50">
        <BrowserRouter>
          <Header />
          <CartSidebar />
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/products" element={<Products />} />
            <Route path="/about" element={<About />} />
            <Route path="/checkout/success" element={<CheckoutSuccess />} />
          </Routes>
        </BrowserRouter>
      </div>
    </CartProvider>
  );
}

export default App;