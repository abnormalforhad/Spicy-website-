from fastapi import FastAPI, APIRouter, HTTPException, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import uuid
from datetime import datetime
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Stripe API Key from environment
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY')
if not STRIPE_API_KEY:
    logging.warning("STRIPE_API_KEY not found in environment")

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Product Model
class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    price: float  # Price in USD
    category: str
    weight: str  # e.g., "100g", "250g", "500g"
    image_url: str
    stock_quantity: int = 100
    featured: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    category: str
    weight: str
    image_url: str
    stock_quantity: int = 100
    featured: bool = False

# Cart Item Model
class CartItem(BaseModel):
    product_id: str
    quantity: int
    price: float

# Order Model
class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_email: str
    items: List[CartItem]
    total_amount: float
    status: str = "pending"  # pending, paid, shipped, delivered
    stripe_session_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Payment Transaction Model
class PaymentTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    order_id: str
    amount: float
    currency: str = "usd"
    payment_status: str = "initiated"  # initiated, paid, failed, expired
    status: str = "pending"  # pending, completed, failed
    customer_email: Optional[str] = None
    metadata: Dict[str, str] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# Checkout Request Model
class CheckoutRequest(BaseModel):
    items: List[CartItem]
    customer_email: str
    origin_url: str

# Product Routes
@api_router.get("/products", response_model=List[Product])
async def get_products():
    products = await db.products.find().to_list(1000)
    return [Product(**product) for product in products]

@api_router.get("/products/featured", response_model=List[Product])
async def get_featured_products():
    products = await db.products.find({"featured": True}).to_list(100)
    return [Product(**product) for product in products]

@api_router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return Product(**product)

@api_router.post("/products", response_model=Product)
async def create_product(product: ProductCreate):
    product_dict = product.dict()
    product_obj = Product(**product_dict)
    await db.products.insert_one(product_obj.dict())
    return product_obj

# Checkout Routes
@api_router.post("/checkout/session")
async def create_checkout_session(checkout_request: CheckoutRequest):
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Payment system not configured")
    
    try:
        # Calculate total amount
        total_amount = sum(item.price * item.quantity for item in checkout_request.items)
        
        # Create order
        order = Order(
            customer_email=checkout_request.customer_email,
            items=checkout_request.items,
            total_amount=total_amount
        )
        await db.orders.insert_one(order.dict())
        
        # Initialize Stripe checkout
        webhook_url = f"{checkout_request.origin_url}/api/webhook/stripe"
        stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
        
        # Create success and cancel URLs
        success_url = f"{checkout_request.origin_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{checkout_request.origin_url}/checkout/cancel"
        
        # Create checkout session request
        metadata = {
            "order_id": order.id,
            "customer_email": checkout_request.customer_email,
            "source": "spice_store"
        }
        
        checkout_session_request = CheckoutSessionRequest(
            amount=total_amount,
            currency="usd",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata
        )
        
        # Create checkout session
        session = await stripe_checkout.create_checkout_session(checkout_session_request)
        
        # Create payment transaction record
        payment_transaction = PaymentTransaction(
            session_id=session.session_id,
            order_id=order.id,
            amount=total_amount,
            customer_email=checkout_request.customer_email,
            metadata=metadata
        )
        await db.payment_transactions.insert_one(payment_transaction.dict())
        
        # Update order with session ID
        await db.orders.update_one(
            {"id": order.id},
            {"$set": {"stripe_session_id": session.session_id}}
        )
        
        return {"url": session.url, "session_id": session.session_id}
        
    except Exception as e:
        logging.error(f"Checkout session creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")

@api_router.get("/checkout/status/{session_id}")
async def get_checkout_status(session_id: str):
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Payment system not configured")
    
    try:
        # Get payment transaction
        transaction = await db.payment_transactions.find_one({"session_id": session_id})
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # If already processed successfully, return current status
        if transaction.get("payment_status") == "paid":
            return CheckoutStatusResponse(
                status="complete",
                payment_status="paid",
                amount_total=int(transaction["amount"] * 100),  # Convert to cents
                currency=transaction["currency"],
                metadata=transaction["metadata"]
            )
        
        # Check status with Stripe
        stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")
        checkout_status = await stripe_checkout.get_checkout_status(session_id)
        
        # Update transaction if status changed
        if checkout_status.payment_status != transaction.get("payment_status"):
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "payment_status": checkout_status.payment_status,
                        "status": "completed" if checkout_status.payment_status == "paid" else transaction["status"],
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Update order status if payment successful
            if checkout_status.payment_status == "paid":
                await db.orders.update_one(
                    {"id": transaction["order_id"]},
                    {"$set": {"status": "paid"}}
                )
        
        return checkout_status
        
    except Exception as e:
        logging.error(f"Checkout status check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to check payment status")

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Payment system not configured")
    
    try:
        body = await request.body()
        stripe_signature = request.headers.get("Stripe-Signature")
        
        stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")
        webhook_response = await stripe_checkout.handle_webhook(body, stripe_signature)
        
        # Update transaction and order based on webhook
        if webhook_response.session_id:
            await db.payment_transactions.update_one(
                {"session_id": webhook_response.session_id},
                {
                    "$set": {
                        "payment_status": webhook_response.payment_status,
                        "status": "completed" if webhook_response.payment_status == "paid" else "failed",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if webhook_response.payment_status == "paid":
                transaction = await db.payment_transactions.find_one({"session_id": webhook_response.session_id})
                if transaction:
                    await db.orders.update_one(
                        {"id": transaction["order_id"]},
                        {"$set": {"status": "paid"}}
                    )
        
        return {"status": "success"}
        
    except Exception as e:
        logging.error(f"Webhook processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

# Orders Routes
@api_router.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str):
    order = await db.orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return Order(**order)

# Initialize sample products
@api_router.post("/init-products")
async def initialize_products():
    # Check if products already exist
    existing_count = await db.products.count_documents({})
    if existing_count > 0:
        return {"message": f"Products already initialized. Count: {existing_count}"}
    
    sample_products = [
        Product(
            name="Premium Red Chili Powder",
            description="Authentic red chili powder made from the finest quality chilies. Perfect for adding heat and flavor to your dishes.",
            price=12.99,
            category="Powders",
            weight="250g",
            image_url="https://images.unsplash.com/photo-1596213812143-ff89bd9ddecd?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzh8MHwxfHNlYXJjaHwzfHxzcGljZXN8ZW58MHx8fG9yYW5nZXwxNzU0MzgzOTQwfDA&ixlib=rb-4.1.0&q=85",
            featured=True
        ),
        Product(
            name="Organic Turmeric Powder",
            description="Pure organic turmeric powder with anti-inflammatory properties. Essential for healthy cooking and traditional recipes.",
            price=15.99,
            category="Powders",
            weight="200g",
            image_url="https://images.unsplash.com/photo-1613216514014-edb92d8e3e8d?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzh8MHwxfHNlYXJjaHwzfHx0dXJtZXJpYyUyMHBvd2RlcnxlbnwwfHx8b3JhbmdlfDE3NTQzODM5NDZ8MA&ixlib=rb-4.1.0&q=85",
            featured=True
        ),
        Product(
            name="Coriander Powder",
            description="Freshly ground coriander seeds with a citrusy aroma. Essential for Indian and Mediterranean cuisine.",
            price=8.99,
            category="Powders",
            weight="150g",
            image_url="https://images.pexels.com/photos/8858686/pexels-photo-8858686.jpeg",
            featured=False
        ),
        Product(
            name="Garam Masala Blend",
            description="Traditional blend of warming spices including cardamom, cinnamon, cloves, and black pepper.",
            price=18.99,
            category="Blends",
            weight="100g",
            image_url="https://images.unsplash.com/photo-1661022166287-1d1ae8dfaec4?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzh8MHwxfHNlYXJjaHwyfHxzcGljZXN8ZW58MHx8fG9yYW5nZXwxNzU0MzgzOTQwfDA&ixlib=rb-4.1.0&q=85",
            featured=True
        ),
        Product(
            name="Black Pepper Powder",
            description="Freshly ground black peppercorns with intense flavor and aroma. The king of spices for your kitchen.",
            price=22.99,
            category="Powders",
            weight="100g",
            image_url="https://images.pexels.com/photos/13705489/pexels-photo-13705489.jpeg",
            featured=False
        ),
        Product(
            name="Cumin Powder",
            description="Earthy and warm cumin powder ground from premium cumin seeds. Perfect for curries and spice blends.",
            price=10.99,
            category="Powders",
            weight="200g",
            image_url="https://images.unsplash.com/photo-1596213812143-ff89bd9ddecd?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzh8MHwxfHNlYXJjaHwzfHxzcGljZXN8ZW58MHx8fG9yYW5nZXwxNzU0MzgzOTQwfDA&ixlib=rb-4.1.0&q=85",
            featured=False
        )
    ]
    
    # Insert products
    for product in sample_products:
        await db.products.insert_one(product.dict())
    
    return {"message": f"Initialized {len(sample_products)} products successfully"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()