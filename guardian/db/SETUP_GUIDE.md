# 🚀 PostgreSQL Setup Guide for Guardian

This guide will help you set up PostgreSQL for Guardian production use while keeping SQLite for development.

## 📋 Prerequisites

1. **PostgreSQL installed** on your system
2. **Python psycopg2** installed: `pip install psycopg2-binary`
3. **Admin access** to PostgreSQL

## 🔧 Step-by-Step Setup

### Step 1: Install PostgreSQL (if not already installed)

**macOS (using Homebrew):**
```bash
brew install postgresql
brew services start postgresql
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Windows:**
Download and install from: https://www.postgresql.org/download/windows/

### Step 2: Set Environment Variables

Add these to your `.env` file:

```bash
# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=guardian
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_postgres_password
POSTGRES_APP_USER=guardian_app
POSTGRES_APP_PASSWORD=your_app_password
```

### Step 3: Run the Setup Script

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/guardian-backend_v2
python db/postgres_setup.py
```

This will:
- ✅ Test PostgreSQL connection
- ✅ Create the `guardian` database
- ✅ Create application user with proper permissions
- ✅ Set up the database structure

### Step 4: Run the Media Tables Migration

```bash
python -c "
from db.postgres_setup import PostgresSetup
setup = PostgresSetup()
success = setup.run_migration('db/migrations/001_create_media_tables.sql')
if success:
    print('✅ Media tables created successfully!')
else:
    print('❌ Failed to create media tables')
"
```

### Step 5: Verify Setup

```bash
python -c "
from db.postgres_setup import PostgresSetup
setup = PostgresSetup()
results = setup.test_tables()
for table, exists in results.items():
    status = '✅' if exists else '❌'
    print(f'{status} {table}: {exists}')
"
```

## 🗄️ Database Structure

After setup, you'll have these tables in PostgreSQL:

### Core Tables
- **projects** - Project management
- **threads** - Thread/Conversation management  
- **chat_threads** - Chat thread registry
- **chat_messages** - Individual chat messages
- **memory_entries** - Memory storage with silos
- **audit_log** - Audit trail

### Media Tables (New!)
- **generated_images** - AI-generated images with prompts
- **uploaded_images** - User-uploaded images with metadata
- **generated_documents** - AI-generated documents with content
- **uploaded_documents** - User-uploaded documents with parsed text

## 🔗 Connection Configuration

### Development (SQLite)
Your existing SQLite setup continues to work for development:
```python
from guardian.core.db import GuardianDB
db = GuardianDB("guardian.db")  # Uses SQLite
```

### Production (PostgreSQL)
For production, you'll want to update your connection logic:
```python
import psycopg2
from psycopg2.extras import RealDictCursor

def get_postgres_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DATABASE", "guardian"),
        user=os.getenv("POSTGRES_APP_USER", "guardian_app"),
        password=os.getenv("POSTGRES_APP_PASSWORD"),
        cursor_factory=RealDictCursor
    )
```

## 🧪 Testing Your Setup

### Quick Connection Test
```python
import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="guardian",
        user="guardian_app",
        password="your_app_password"
    )
    print("✅ PostgreSQL connection successful!")
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

### Test Media Operations
```python
from guardian.core.db import GuardianDB
from guardian.db.models import UploadedImage
import uuid

# Initialize database connection
db = GuardianDB("postgresql://guardian_app:password@localhost:5432/guardian")

# Test creating an uploaded image using ORM
image_id = str(uuid.uuid4())
with db.get_session() as session:
    image = UploadedImage(
        id=image_id,
        project_id=1,
        thread_id=1,
        user_id="test_user",
        src_url="/media/images/test.jpg",
        filename="test.jpg",
        filesize=1024,
        mime_type="image/jpeg"
    )
    session.add(image)
    session.commit()
    print(f"✅ Created image: {image_id}")

# Or use the REST API
import requests
response = requests.post(
    "http://localhost:8888/api/media/upload/image",
    files={"file": open("test.jpg", "rb")},
    data={"project_id": 1, "thread_id": 1}
)
print(f"✅ API response: {response.json()}")
```

## 🔧 Troubleshooting

### Connection Issues
```bash
# Check if PostgreSQL is running
pg_isready -h localhost -p 5432

# Check database exists
psql -U postgres -d guardian -c "SELECT current_database();"

# Check tables exist
psql -U postgres -d guardian -c "\dt"
```

### Permission Issues
```bash
# Reset permissions
psql -U postgres -d guardian -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO guardian_app;"
psql -U postgres -d guardian -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO guardian_app;"
```

### Migration Issues
If migrations fail, you can manually run them:
```bash
psql -U postgres -d guardian -f db/migrations/001_create_media_tables.sql
```

## 🚀 Next Steps

1. **Update your application code** to use PostgreSQL connections in production
2. **Configure your deployment** to use PostgreSQL environment variables
3. **Set up database backups** and monitoring
4. **Consider connection pooling** for better performance

## 📚 Additional Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [psycopg2 Documentation](https://www.psycopg.org/docs/)
- [PostgreSQL Best Practices](https://wiki.postgresql.org/wiki/Best_practices)

Your Guardian system is now ready for production with PostgreSQL! 🎉
