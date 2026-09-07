# PharmaMed - OTC Pharmacy E-Commerce Web Application

## Video Demo
[**PharmaMed Video Demo on YouTube**](https://youtu.be/lYsaer4rReY)

## Description
PharmaMed is a fully responsive web-based pharmacy e-commerce application developed as a final project for the HarvardX: CS50's Introduction to Computer Science course.

The aim of the project was to apply programming, database, and web development concepts by creating a functional online store for over-the-counter (OTC) healthcare products.

The application allows users to browse, search, and purchase products, and provides user and administrator authentication, product catalog management, order processing, and inventory tracking through an intuitive web interface. 

This project demonstrates the integration of front-end and back-end web technologies, database management, and user interaction features.

## Features

### 1. Customer features

- User registration and authentication
- Product browsing by category
- Product search and filtering
- Product detail pages
- Shopping cart management
- Order placement
- Orders history
- Shipping addresses management

### 2. Administrative features

- Administrator authentication
- Product addition, editing and deactivation
- Inventory management
- Customer orders management

## Technology Stack

| Technology | Purpose |
|------------|---------|
| Visual Studio Code | Development environment |
| Git | Version Control |
| GitHub | Repository hosting |
| Python 3.10.12 | Backend programming |
| Flask 3.1.3 | Web framework |
| SQLite 3 | Data storage |
| HTML5 | Page structure |
| CSS3 | Styling |
| Bootstrap 5 | CSS framework |
| JavaScript | Client-side interactivity |
| Jinja2 3.1.6 | Dynamic page rendering |

## Database Design

The application uses a relational SQLite database consisting of the following ten tables:

| Table | Purpose |
|---------|---------|
| categories | Product categories and subcategories |
| brands | Product brands/manufacturers |
| products | OTC product catalog |
| users | Customer accounts |
| carts | Shopping carts |
| cart_items | Products in shopping carts |
| addresses | Customer shipping addresses |
| orders | Customer orders |
| order_items | Products in orders |
| admins | Administrator accounts |

The database was designed to separate product information, customer information, shopping cart data, and order history into distinct entities in order to reduce data duplication and improve maintainability.

Key relationships include:

- Categories can contain subcategories through a self-referencing relationship.
- Products belong to a category and a brand.
- Users can maintain a shopping cart and multiple shipping addresses.
- Orders are associated with users and contain one or more order items.

**Design decison:** The orders table stores a copy of the shipping address information at the time of purchase. This design ensures that order records remain complete even if customers later modify or delete addresses from their accounts. Therefore, the address_id field is not enforced as a foreign key constraint.
Similarly, the order items table stores product name, pack size and price. This ensures that past orders still show exactly what the customer purchased at the time of the transaction even if a product's name, packaging, or price changes later or a product is removed from catalog.

## Project Structure

```
.
├── README.md
├── app/
│   ├── __init__.py
│   ├── extensions.py
│   ├── models/
│   ├── routes/
│   ├── services/
│   ├── static/
│   ├── templates/
│   └── utils/
├── create_admin.py
├── pharmamed.db
├── products.csv
├── requirements.txt
├── run.py
└── schema.sql
```

The following sections describe the purpose of each major file and directory in the project.

### Root directory

#### run.py

The entry point of the application. It imports the Flask application and starts the development server.

#### schema.sql

Contains the SQL statements used to create the application's database schema, including tables, constraints, and relationships.

#### pharmamed.db

SQLite database file used by the application during development.

#### products.csv

CSV file containing the initial product catalog, imported into the SQLite database to populate the products table.

#### create_admin.py

Utility script used to create administrator accounts. Administrators cannot register through the web interface and must be created manually using this script.

#### requirements.txt

Lists all Python dependencies required to run the project.

### app/

This directory contains the main application code.

**Design decision:** One of the primary design goals of this project was to separate responsibilities across different modules. Flask route handlers are responsible for processing HTTP requests, validating user input, and rendering templates. Business logic and database operations are implemented in service modules, while reusable helper functions are placed in utility modules. This organization reduces code duplication, improves readability, and makes the application easier to maintain and extend.

#### init.py

Creates and configures the Flask application. It registers blueprints, initializes extensions, configures the application, and sets up shared template context and database connection management.

#### extensions.py

Contains shared Flask extensions used throughout the application such as Flask-Login LoginManager.

### app/models/

#### user.py

Defines the Flask-Login User model and the user loader used to restore authenticated users from the session.

### app/routes/

Contains all Flask route handlers responsible for processing HTTP requests and returning responses.

#### main.py

Handles the application's public pages, including the home page and its featured content.

#### auth.py

Handles user registration, login, logout, and password recovery.

#### products.py

Manages product browsing, search, filtering, results sorting, breadcrumb navigation, pagination, and product detail pages.

#### cart.py

Provides routes for adding products to the cart, displaying cart contents, and updating item quantities or removing items.

**Design decision:** The shopping cart was designed to support both guest and authenticated users. Guest carts are stored in the user's session, while authenticated users' carts are stored in the database. When a guest logs in or registers, the session cart is automatically merged with the user's database cart. This approach allows customers to begin shopping without creating an account while preserving their selections after authentication.

#### orders.py

Handles the checkout workflow, including address selection, order validation, stock reservation, order creation, and order confirmation.

**Design decision:** Order creation is performed within a database transaction. If an error occurs during order processing, all pending database changes are rolled back to prevent incomplete orders or inconsistent inventory data.

#### account.py

Manages customer profiles, addresses, order history, and account security.

#### admin.py

Provides administrative functionality for managing products, inventory, and orders.

**Design decision:** Customer and administrator authentication are implemented separately. Customers authenticate through Flask-Login, while administrators use a dedicated session protected by a custom admin_required decorator. Administrator accounts cannot be self-registered and must be created manually using the ```create_admin.py``` utility. This separation simplifies permission management and prevents customers from obtaining administrative privileges. Products are also soft-deleted (deactivated rather than removed) to preserve inventory history.

### app/services/

Contains business logic and database operations.  

#### product_service.py

Provides product, category, and brand data management, along with inventory-related operations.

#### cart_service.py

Implements shopping cart functionality for guest and authenticated users.

#### order_service.py

Provides business logic for checkout, order creation, and order retrieval and management.

**Design decision:** When an order is created, the selected shipping address is copied into the orders table rather than relying solely on the user's address record. This preserves the shipping information exactly as it was at the time of purchase, even if the customer later edits or deletes their saved addresses.

#### user_service.py

Handles user account management and authentication-related operations.

#### address_service.py

Manages user shipping addresses, including creation, retrieval, updates, deletion, and default address handling.

#### admin_service.py

Handles administrator account management and authentication-related database operations.

### app/utils/

Contains helper functions used throughout the application.

#### db.py

Manages database connection and initialization utilities.

#### validators.py

Defines reusable validation patterns for user input, including email addresses and passwords.

#### decorators.py

Provides a custom decorator used to protect routes and enforce administrator authentication.

#### formatting.py

Contains an helper function for date formatting displayed throughout the application.

#### uploads.py

Defines the allowed image file formats and provides an helper function for validating uploaded files.

#### query_helpers.py

Provides reusable helper functions for product  filtering, sorting and counting, and pagination.

#### categories.py

Provides helper functions for working with the product category hierarchy, including navigation menu generation and breadcrumb creation.

### app/templates/

Contains Jinja2 HTML templates used to render the user interface.

### app/static/

Contains static assets including:

- CSS stylesheet
- JavaScript files
- Product images and icons

## Installation 

1. Clone the repository.
2. Create and activate a virtual environment.
3. Install the required dependencies:  
    ```pip install -r requirements.txt```
4. (Optional) Create an administrator account:
   ```python create_admin.py```
5. Run the application:  
    ```flask run```
6. Open your browser and navigate to:
   ```http://127.0.0.1:5000```

## Challenges Encountered

Some challenges during development included:

- Designing the database schema
- Implementing pagination and product filtering and sorting
- Managing user sessions
- Handling shopping cart functionality

## Lessons Learned

Through this project, I gained practical experience with:

- Flask web development
- SQL database design
- Template rendering using Jinja2
- Front-end and back-end integration

## Known Limitations

For demonstration purposes, password reset links are displayed to the user through a flash message instead of being sent by email. In a production application, reset tokens should be delivered through a trusted email service to ensure that only the account owner can access the password reset link.

Payment processing is not implemented. Orders are created without integrating an external payment gateway. Future versions could support providers such as Stripe or PayPal.

## Fututre Improvements

- Add indexes to frequently queried columns to improve search and query performance as the database grows
- Email notifications for password reset and order confirmation
- Product reviews and ratings
- Product recommendation system
- Payment gateway integration

## AI Assistance 

ChatGPT was used throughout the development of PharmaMed as a supplementary development and learning tool. It was used for tasks such as discussing implementation approaches, debugging, reviewing code structure, and suggesting improvements.

All generated suggestions were reviewed and tested before being incorporated into the application. The final implementation and design decisions remain the responsibility of the author.

## Author

Sarah Guerreiro

GitHub: https://github.com/sarah-guerreiro
