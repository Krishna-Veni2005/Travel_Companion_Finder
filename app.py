from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os

# App setup
app = Flask(__name__)
app.secret_key = 'a3f47b9e6d4f2d8c3b1c6e8a7f2e1d0f'

# Ensure database directory exists
database_dir = os.path.join(os.path.dirname(__file__), "database")
if not os.path.exists(database_dir):
    os.makedirs(database_dir)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(database_dir, "travel_companion.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Don't forget to include this loader function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def accept_friend_request(user1, user2):
    # Create mutual friendships
    f1 = Friendship(user_id=user1.id, friend_id=user2.id)
    f2 = Friendship(user_id=user2.id, friend_id=user1.id)
    db.session.add_all([f1, f2])
    db.session.commit()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(15))  # Will make required in UI
    gender = db.Column(db.String(10))  # Will make required in UI
    dob = db.Column(db.Date)  # Will make required in UI
    destination = db.Column(db.String(150))
    travel_date = db.Column(db.Date)
    profile_completed = db.Column(db.Boolean, default=False)  # New field to track profile completion
    is_public = db.Column(db.Boolean, default=False)

    # Users that this user has friended
    friends = db.relationship(
        'User', 
        secondary='friendship',
        primaryjoin='User.id == Friendship.user_id',
        secondaryjoin='User.id == Friendship.friend_id',
        back_populates='friend_of'
    )
    
    # Users who have friended this user
    friend_of = db.relationship(
        'User',
        secondary='friendship',
        primaryjoin='User.id == Friendship.friend_id',
        secondaryjoin='User.id == Friendship.user_id',
        back_populates='friends'
    )

class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<Friendship {self.user_id} - {self.friend_id}>'


# Traveler model for storing search/filter data
class Traveler(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    username = db.Column(db.String(150))
    destination = db.Column(db.String(150))
    travel_date = db.Column(db.Date)
    gender = db.Column(db.String(10))
    age = db.Column(db.Integer)
    interests = db.Column(db.String(255))
    origin_city = db.Column(db.String(100))
    companion_type = db.Column(db.String(50))
    user = db.relationship('User', backref='traveler_searches', lazy=True)

    _table_args_ = (
        db.Index('ix_user_id', 'user_id'),
    )


class FriendRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    sender = db.Column(db.String(150))
    receiver = db.Column(db.String(150))
    status = db.Column(db.String(20), default='pending')  # 'pending', 'accepted', 'rejected'
    
    # Add relationships for easier access
    sender_user = db.relationship('User', foreign_keys=[sender_id])
    receiver_user = db.relationship('User', foreign_keys=[receiver_id])


# Add Message model
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        new_user = User(username=username, email=email, password=password, profile_completed=False)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in and complete your profile.', 'success')
        return redirect('/login')
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            login_user(user)
            if not user.profile_completed:
                flash('Please complete your profile before continuing.', 'info')
                return redirect('/profile')
            return redirect('/home')
        else:
            flash('Invalid email or password', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect('/login')


@app.route('/home')
@login_required
def home():
    # Check if profile is completed
    if not current_user.profile_completed:
        flash('Please complete your profile first.', 'warning')
        return redirect('/profile')
    return render_template('home.html', username=current_user.username)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Get form data
        phone = request.form['phone']
        gender = request.form['gender']
        dob_str = request.form['dob']
        is_public = request.form.get('is_public') == 'on'
        
        # Validate required fields
        if not phone or not gender or not dob_str:
            flash('Phone number, gender, and date of birth are all required!', 'danger')
            return redirect('/profile')
        
        try:
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
        except ValueError:
            flash('Invalid date format!', 'danger')
            return redirect('/profile')
        
        # Update user profile
        current_user.phone = phone
        current_user.gender = gender
        current_user.dob = dob
        current_user.is_public = is_public
        current_user.profile_completed = True
        db.session.commit()
        
        flash('Profile updated successfully!', 'success')
        return redirect('/home')

    # Get all friends for the current user
    friends = current_user.friends

    # Get friend requests received by the current user
    received_requests = FriendRequest.query.filter_by(receiver_id=current_user.id).all()
    
    # Get friend requests sent by the current user
    sent_requests = FriendRequest.query.filter_by(sender_id=current_user.id).all()

    return render_template('profile.html', 
                          user=current_user, 
                          friends=friends,
                          received_requests=received_requests,
                          sent_requests=sent_requests)

@app.route('/remove_friend/<int:friend_id>', methods=['POST'])
@login_required
def remove_friend(friend_id):
    # Fetch the friend to be removed
    friend = User.query.get(friend_id)
    
    if friend and friend != current_user:
        # Find both directions of the friendship
        friendship1 = Friendship.query.filter(
            (Friendship.user_id == current_user.id) & (Friendship.friend_id == friend.id)
        ).first()
        
        friendship2 = Friendship.query.filter(
            (Friendship.user_id == friend.id) & (Friendship.friend_id == current_user.id)
        ).first()
        
        # Remove both friendship records from the database
        if friendship1:
            db.session.delete(friendship1)
        
        if friendship2:
            db.session.delete(friendship2)
        
        # Also delete any existing friend requests between these users (in both directions)
        FriendRequest.query.filter(
            ((FriendRequest.sender_id == current_user.id) & (FriendRequest.receiver_id == friend.id)) |
            ((FriendRequest.sender_id == friend.id) & (FriendRequest.receiver_id == current_user.id))
        ).delete()
            
        db.session.commit()
        flash(f'Removed {friend.username} from your friends.', 'success')
    else:
        flash('Invalid operation.', 'danger')

    return redirect(url_for('profile'))


@app.route('/chat/<int:user_id>')
@login_required
def chat(user_id):
    # Check if profile is completed
    if not current_user.profile_completed:
        flash('Please complete your profile first.', 'warning')
        return redirect('/profile')
    
    other_user = User.query.get_or_404(user_id)
    messages = Message.query.filter_by(receiver_id=user_id).all()
    return render_template('chat.html', other_user=other_user, messages=messages)


@app.route('/public-profiles')
@login_required
def public_profiles():
    # Check if profile is completed
    if not current_user.profile_completed:
        flash('Please complete your profile first.', 'warning')
        return redirect('/profile')
        
    public_users = User.query.filter(User.is_public == True, User.id != current_user.id).all()
    return render_template('public_profiles.html', public_users=public_users)


@app.route('/my-searches')
@login_required
def my_searches():
    # Check if profile is completed
    if not current_user.profile_completed:
        flash('Please complete your profile first.', 'warning')
        return redirect('/profile')
    
    # Get all the traveler searches by the current user
    user_searches = Traveler.query.filter_by(user_id=current_user.id).order_by(Traveler.id.desc()).all()
    
    search_matches = []

    # Iterate over each search of the current user
    for search in user_searches:
        # Find travelers who match the search criteria
        matches = Traveler.query.filter(
            Traveler.user_id != current_user.id,  # Exclude current user
            Traveler.destination == search.destination,
            Traveler.travel_date == search.travel_date
        ).all()
        
        for match in matches:
            # Ensure user relationship is loaded
            match.user = User.query.get(match.user_id)

        # Add the search and its matches to the list
        search_matches.append({
            "search": search,
            "matches": matches
        })

    return render_template('my_searches.html', search_matches=search_matches)



@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    # Check if profile is completed
    if not current_user.profile_completed:
        flash('Please complete your profile first.', 'warning')
        return redirect('/profile')
    
    username = current_user.username
    destination = request.form.get("destination")
    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")
    gender = request.form.get("gender")
    min_age = request.form.get("min_age")
    max_age = request.form.get("max_age")
    interests = request.form.get("interests")
    origin_city = request.form.get("origin_city")
    companion_type = request.form.get("companion_type")
    
    # Convert travel date
    travel_date_obj = None
    if start_date:
        try:
            travel_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid travel date format.", "danger")
            return redirect("/home")
    
    # Save the current user's search
    traveler = Traveler(
        user_id=current_user.id,
        username=username,
        destination=destination,
        travel_date=travel_date_obj,
        gender=gender,
        age=None,
        interests=interests,
        origin_city=origin_city,
        companion_type=companion_type
    )
    
    db.session.add(traveler)
    db.session.commit()
    
    # Find other users who have searched for the same destination (excluding current user)
    query = Traveler.query.filter(
        Traveler.username != current_user.username,
        Traveler.destination == destination
    )
    
    if travel_date_obj:
        query = query.filter(Traveler.travel_date == travel_date_obj)
    
    if gender:
        query = query.filter(Traveler.gender == gender)
    
    matched_travelers = query.all()
    
    return render_template("search_res.html", travelers=matched_travelers, destination=destination)


@app.route('/delete-search/<int:id>', methods=['POST'])
@login_required
def delete_search(id):
    search = Traveler.query.get_or_404(id)
    
    if search.username != current_user.username:
        flash("You can only delete your own searches.", "danger")
        return redirect('/my-searches')

    db.session.delete(search)
    db.session.commit()
    flash("Search deleted successfully.", "success")
    return redirect('/my-searches')


@app.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    # Get the actual user object by ID instead of using the proxy
    user_id = current_user.id
    user = User.query.get(user_id)
    
    if user:
        # Delete all traveler searches associated with this user
        Traveler.query.filter_by(user_id=user.id).delete()
        
        # Delete all friend requests associated with this user
        FriendRequest.query.filter((FriendRequest.sender_id == user.id) | 
                                  (FriendRequest.receiver_id == user.id)).delete()
        
        # Delete all friendship relationships
        Friendship.query.filter((Friendship.user_id == user.id) | 
                               (Friendship.friend_id == user.id)).delete()
        
        # Log the user out
        logout_user()
        
        # Delete the user
        db.session.delete(user)
        db.session.commit()
        
        flash("Your account has been deleted.", "info")
        return redirect('/register')
    else:
        flash("Error deleting account.", "danger")
        return redirect('/profile')


@app.route('/send_request/<int:receiver_id>', methods=['POST'])
@login_required
def send_request(receiver_id):
    # Check if profile is completed
    if not current_user.profile_completed:
        flash('Please complete your profile first.', 'warning')
        return redirect('/profile')
    
    receiver = User.query.get_or_404(receiver_id)
    
    # Prevent sending to self
    if receiver.id == current_user.id:
        flash("You cannot send a request to yourself.", "warning")
        return redirect(url_for('my_searches'))
    
    # Check if already sent or received
    existing_request = FriendRequest.query.filter(
        ((FriendRequest.sender_id == current_user.id) & (FriendRequest.receiver_id == receiver.id)) |
        ((FriendRequest.sender_id == receiver.id) & (FriendRequest.receiver_id == current_user.id))
    ).first()
    
    if existing_request:
        flash("A friend request already exists between you two.", "info")
        return redirect(url_for('my_searches'))
    
    # Create friend request
    friend_request = FriendRequest(
        sender_id=current_user.id,
        receiver_id=receiver.id,
        sender=current_user.username,
        receiver=receiver.username,
        status='pending'
    )
    db.session.add(friend_request)
    db.session.commit()
    flash("Friend request sent!", "success")
    return redirect(url_for('my_searches'))


@app.route('/respond-request/<int:request_id>/<action>', methods=['POST'])
@login_required
def respond_request(request_id, action):
    req = FriendRequest.query.get_or_404(request_id)
    
    # Make sure the current user is the receiver of the request
    if req.receiver_id == current_user.id:
        if action == 'accept':
            # Update request status to accepted
            req.status = 'accepted'
            
            # Create mutual friendship between the users
            sender = User.query.get(req.sender_id)
            if sender:
                # Use the accept_friend_request helper function to create mutual friendship
                accept_friend_request(sender, current_user)
                flash(f"You are now friends with {sender.username}", "success")
            
        elif action == 'reject':
            req.status = 'rejected'
            flash("Friend request rejected", "info")
            
        db.session.commit()
    else:
        flash("You can only respond to your own friend requests", "warning")
        
    return redirect('/profile')

# Create database tables if they don't exist
if __name__ == '__main__':
    if not os.path.exists('database'):
        os.makedirs('database')
    with app.app_context():
        db.create_all()
    app.run(debug=True)