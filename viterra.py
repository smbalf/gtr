import pyxel
import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from enum import Enum
import uuid


class AssetClass(Enum):
    AGRICULTURE = "AGRICULTURE"
    SOFTS = "SOFTS"
    ENERGY = "ENERGY"
    CURRENCY = "CURRENCY"
    FINANCIAL = "FINANCIAL"

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class PositionType(Enum):
    SPECULATIVE = "SPECULATIVE"
    HEDGE = "HEDGE"

@dataclass
class ContractSpecification:
    name: str  # Contract name (e.g., "CORN")
    description: str
    asset_class: AssetClass
    contract_size: float  # Size of one contract
    tick_size: float     # Minimum price movement
    currency: str
    unit: str
    basis_conversion: float
    initial_margin_pct: float = 0.10
    min_price_increment: float = 0.0001
    weeks_to_expiry: List[int] = field(default_factory=lambda: [13, 26, 39, 52])

    def __eq__(self, other):
        """Define how two ContractSpecifications should be compared for equality.
        We'll consider them equal if they have the same name, as that's unique."""
        if not isinstance(other, ContractSpecification):
            return False
        return self.name == other.name

    def __hash__(self):
        """Define how to create a unique hash value for a ContractSpecification.
        This is needed when using ContractSpecification objects in sets or as 
        dictionary keys."""
        return hash(self.name)

# In the FuturesContract class
@dataclass
class FuturesContract:
    spec: ContractSpecification
    expiry_week: int
    expiry_year: int
    price: float
    contract_id: str = field(init=False)
    last_price: float = None  # Changed from 0.0 to None
    high: float = field(init=False)
    low: float = field(init=False)
    #open_interest: int = 0
    bid: float = field(init=False)
    ask: float = field(init=False)
    volume: int = 0
    price_history: List[Tuple[int, float]] = field(default_factory=list)

    def __post_init__(self):
        """Initialize contract with proper prices"""
        self.contract_id = f"{self.spec.name}W{self.expiry_week}-{self.expiry_year}"
        self.last_price = self.price  # Initialize last price to current price
        self.high = self.price        # Initialize high to current price
        self.low = self.price         # Initialize low to current price
        self.bid = self.price - (self.spec.tick_size * 2)  # Initialize bid
        self.ask = self.price + (self.spec.tick_size * 2)  # Initialize ask
        self.price_history.append((0, self.price))  # Add initial price to history

    def update_price(self, new_price: float):
        """Update contract price and related statistics"""
        if self.last_price is None:  # If last_price not set
            self.last_price = new_price
        else:
            self.last_price = self.price
            
        self.price = new_price
        self.high = max(self.high, new_price)
        self.low = min(self.low, new_price)
        self.price_history.append((0, new_price))
        
        # Update bid/ask
        spread = self.spec.tick_size * 2
        self.bid = new_price - spread/2
        self.ask = new_price + spread/2

@dataclass
class FuturesOrder:
    """Represents a futures order"""
    contract_id: str
    order_type: OrderType
    side: OrderSide
    quantity: int
    price: Optional[float] = None
    position_type: PositionType = PositionType.SPECULATIVE
    timestamp: int = 0
    status: str = "PENDING"
    filled_quantity: int = 0
    filled_price: float = 0.0

@dataclass
class FuturesPosition:
    """
    Represents a futures position with proper P&L calculation including contract size
    """
    contract_id: str
    quantity: int  # Positive for long, negative for short
    average_price: float
    position_type: PositionType
    spec: ContractSpecification  # Added to access contract specifications
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    margin_held: float = 0.0
    
    def update_pnl(self, current_price: float):
        """Update position P&L based on current market price, accounting for contract size"""
        if self.quantity == 0:
            self.unrealized_pnl = 0.0
            return
            
        price_change = current_price - self.average_price
        # Calculate P&L including contract size multiplier
        contract_value = abs(self.quantity) * price_change * self.spec.contract_size
        self.unrealized_pnl = contract_value if self.quantity > 0 else -contract_value
class FuturesManager:
    """Manages futures trading, positions, and risk"""
    def __init__(self, game):
        self.game = game
        self.contract_specs: Dict[str, ContractSpecification] = {}
        self.active_contracts: Dict[str, FuturesContract] = {}
        self.positions: Dict[str, FuturesPosition] = {}
        self.orders: List[FuturesOrder] = []
        self.total_margin_required: float = 0.0
        self._last_update_week = 1  # Initialize the last update week
        self.initialize_contracts()
    
    def initialize_contracts(self):
        """Initialize all contract specifications"""
        # AGRICULTURE
        self.setup_grain_contracts()
        # SOFTS
        self.setup_softs_contracts()
        # ENERGY
        self.setup_energy_contracts()
        # CURRENCIES
        self.setup_currency_contracts()
        # FINANCIALS
        self.setup_financial_contracts()

    def setup_grain_contracts(self):
        """Setup agricultural futures with corrected decimal places"""
        # CORN
        self.create_contracts_for_spec(ContractSpecification(
            name="CORN",
            description="Corn Futures - 5,000 Metric Tons",
            asset_class=AssetClass.AGRICULTURE,
            contract_size=5000,
            tick_size=0.25,  # Changed from 0.25 to match real-world
            currency="USD",
            unit="MT",
            basis_conversion=1.0,
            initial_margin_pct=0.10,
            min_price_increment=0.25  # Added to ensure proper price formatting
        ))

        # WHEAT
        self.create_contracts_for_spec(ContractSpecification(
            name="WHEAT",
            description="Wheat Futures - 5,000 Metric Tons",
            asset_class=AssetClass.AGRICULTURE,
            contract_size=5000,
            tick_size=0.25,  # Changed from 0.25 to match real-world
            currency="USD",
            unit="MT",
            basis_conversion=1.0,
            initial_margin_pct=0.10,
            min_price_increment=0.25  # Added to ensure proper price formatting
        ))

        # SOYBEANS
        self.create_contracts_for_spec(ContractSpecification(
            name="SOYBEAN",
            description="Soybean Futures - 5,000 Metric Tons",
            asset_class=AssetClass.AGRICULTURE,
            contract_size=5000,
            tick_size=0.25,  # Changed from 0.25 to match real-world
            currency="USD",
            unit="MT",
            basis_conversion=1.0,
            initial_margin_pct=0.10,
            min_price_increment=0.25  # Added to ensure proper price formatting
        ))

    def setup_softs_contracts(self):
        """Setup softs futures contracts with proper price handling and contract sizes"""
        # Sugar #11
        self.create_contracts_for_spec(ContractSpecification(
            name="SUGAR",
            description="Sugar #11 - 112,000 Pounds",
            asset_class=AssetClass.SOFTS,
            contract_size=112000,  # 112,000 pounds
            tick_size=0.01,  # 0.01 cents per pound
            currency="USD",
            unit="LBS",
            basis_conversion=2204.62,  # For MT conversion
            initial_margin_pct=0.10,
            min_price_increment=0.01  # Ensure proper price formatting
        ))

        # Coffee
        self.create_contracts_for_spec(ContractSpecification(
            name="COFFEE",
            description="Coffee - 37,500 Pounds",
            asset_class=AssetClass.SOFTS,
            contract_size=3750,  # 37,500 pounds
            tick_size=0.05,  # 0.05 cents per pound
            currency="USD",
            unit="LBS",
            basis_conversion=2204.62,  # For MT conversion
            initial_margin_pct=0.10,
            min_price_increment=0.05  # Ensure proper price formatting
        ))

        # Cotton
        self.create_contracts_for_spec(ContractSpecification(
            name="COTTON",
            description="Cotton - 50,000 Pounds",
            asset_class=AssetClass.SOFTS,
            contract_size=50000,  # 50,000 pounds
            tick_size=0.01,  # 0.01 cents per pound
            currency="USD",
            unit="LBS",
            basis_conversion=2204.62,  # For MT conversion
            initial_margin_pct=0.10,
            min_price_increment=0.01  # Ensure proper price formatting
        ))

    def setup_energy_contracts(self):
        """Setup energy futures contracts with proper barrel sizes"""
        # WTI Crude Oil
        self.create_contracts_for_spec(ContractSpecification(
            name="WEST TEXAS OIL",
            description="WTI Crude Oil - 1,000 Barrels",
            asset_class=AssetClass.ENERGY,
            contract_size=5000,  # 1,000 barrels
            tick_size=0.01,  # 1 cent per barrel
            currency="USD",
            unit="BBL",  # Changed to BBL (barrels)
            basis_conversion=7.33  # Barrels to MT conversion
        ))

        # Brent Crude
        self.create_contracts_for_spec(ContractSpecification(
            name="BRENT OIL",
            description="Brent Crude Oil - 1,000 Barrels",
            asset_class=AssetClass.ENERGY,
            contract_size=5000,  # 1,000 barrels
            tick_size=0.01,  # 1 cent per barrel
            currency="USD",
            unit="BBL",
            basis_conversion=7.33
        ))

        # Natural Gas
        self.create_contracts_for_spec(ContractSpecification(
            name="NATURAL GAS",
            description="Natural Gas - 10,000 MMBtu",
            asset_class=AssetClass.ENERGY,
            contract_size=100000,  # 10,000 MMBtu
            tick_size=0.001,  # 0.1 cent per MMBtu
            currency="USD",
            unit="MMBTU",  # Changed to MMBTU
            basis_conversion=1.0
        ))

    def setup_currency_contracts(self):
        """Setup currency futures with corrected contract sizes and decimal places"""
        # EURUSD
        self.create_contracts_for_spec(ContractSpecification(
            name="EURUSD",
            description="Euro FX - €125,000",
            asset_class=AssetClass.CURRENCY,
            contract_size=250000,  # €125,000
            tick_size=0.00005,  # Increased precision for better spread
            currency="EURUSD",
            unit="EURUSD",
            basis_conversion=1.0,
            initial_margin_pct=0.05  # 5% margin
        ))

        # GBPUSD
        self.create_contracts_for_spec(ContractSpecification(
            name="GBPUSD",
            description="British Pound - £62,500",
            asset_class=AssetClass.CURRENCY,
            contract_size=250000,  # £62,500
            tick_size=0.00005,  # Increased precision
            currency="GBPUSD",
            unit="GBPUSD",
            basis_conversion=1.0,
            initial_margin_pct=0.05  # 5% margin
        ))

        # USDJPY - Fixed to use proper sizing
        self.create_contracts_for_spec(ContractSpecification(
            name="USDJPY",
            description="Japanese Yen - ¥12,500,000",
            asset_class=AssetClass.CURRENCY,
            contract_size= 7500, # Changed to USD equivalent
            tick_size=0.001,  # 3 decimals for JPY
            currency="USDJPY",
            unit="USDJPY",
            basis_conversion=1.0,
            initial_margin_pct=0.05  # 5% margin
        ))

    def setup_financial_contracts(self):
        """Setup financial futures with proper point values"""
        # 10-Year Treasury
        self.create_contracts_for_spec(ContractSpecification(
            name="10YR TREASURY",
            description="10-Year Treasury - $100,000 Face Value",
            asset_class=AssetClass.FINANCIAL,
            contract_size=1000,  # Adjusted to properly handle point value
            tick_size=0.015625,  # 1/32 of a point
            currency="USD",
            unit="POINTS",
            basis_conversion=1.0,
            initial_margin_pct=0.03  # Changed to 3%
        ))

        # 5-Year Treasury
        self.create_contracts_for_spec(ContractSpecification(
            name="5YR TREASURY",
            description="5-Year Treasury - $100,000 Face Value",
            asset_class=AssetClass.FINANCIAL,
            contract_size=1000,  # Adjusted for point value
            tick_size=0.0078125,  # 1/32 of a point
            currency="USD",
            unit="POINTS",
            basis_conversion=1.0,
            initial_margin_pct=0.03  # Changed to 3%
        ))

    def create_contracts_for_spec(self, spec: ContractSpecification):
        """Create contracts with proper forward curve structure"""
        current_week = self.game.market.current_week
        current_year = self.game.market.year
        
        # Get base price for the commodity
        base_price = self._get_physical_price(spec.name)
        if not base_price:
            base_price = self._get_initial_price(spec.name)
        
        # Track existing expiries to avoid duplicates
        existing_expiries = set(
            (contract.expiry_week, contract.expiry_year)
            for contract in self.active_contracts.values()
            if contract.spec.name == spec.name
        )
        
        # Generate contracts for each expiry week if they don't exist
        for weeks_forward in spec.weeks_to_expiry:
            expiry_week = current_week + weeks_forward
            expiry_year = current_year
            
            # Handle year rollover
            while expiry_week > 52:
                expiry_week -= 52
                expiry_year += 1
                
            # Skip if this expiry already exists
            if (expiry_week, expiry_year) in existing_expiries:
                continue
                
            contract_id = f"{spec.name}W{expiry_week}-{expiry_year}"
            
            # Calculate forward premium based on time to expiry and asset class
            forward_price = base_price
            
            if spec.asset_class == AssetClass.AGRICULTURE:
                # Storage cost per week (0.15%)
                storage_cost = 0.0015 * weeks_forward
                
                # Interest cost (annual rate of 7.5% divided into weeks)
                interest_cost = (0.075 / 52) * weeks_forward
                
                # Seasonal adjustment based on expiry week
                seasonal_factor = self._calculate_seasonal_factor(spec.name, expiry_week)
                
                # Combine all factors
                forward_price = base_price * (1 + storage_cost + interest_cost + seasonal_factor)
            
            # Create the contract with calculated forward price
            self.active_contracts[contract_id] = FuturesContract(
                spec=spec,
                expiry_week=expiry_week,
                expiry_year=expiry_year,
                price=round(forward_price, 2),
                last_price=round(forward_price, 2)
            )

    def _calculate_seasonal_factor(self, commodity: str, expiry_week: int) -> float:
        """Calculate seasonal price adjustments based on commodity and time of year"""
        seasonal_patterns = {
            "CORN": {
                "peak_weeks": [10, 11, 12, 13],  # Pre-harvest weeks
                "low_weeks": [40, 41, 42, 43]    # Post-harvest weeks
            },
            "WHEAT": {
                "peak_weeks": [20, 21, 22, 23],
                "low_weeks": [32, 33, 34, 35]
            },
            "SOYBEAN": {
                "peak_weeks": [15, 16, 17, 18],
                "low_weeks": [37, 38, 39, 40]
            }
        }
        
        if commodity not in seasonal_patterns:
            return 0.0
            
        pattern = seasonal_patterns[commodity]
        
        if expiry_week in pattern["peak_weeks"]:
            return 0.03  # 3% premium during peak weeks
        elif expiry_week in pattern["low_weeks"]:
            return -0.02  # 2% discount during harvest
            
        return 0.0

    def _get_physical_price(self, commodity: str) -> Optional[float]:
        """Get current physical market price for a commodity"""
        relevant_quotes = [
            quote for (com, _), quote in self.game.market.fob_markets.items()
            if com == commodity and quote.has_valid_quote()
        ]
        
        if relevant_quotes:
            return sum(q.bid for q in relevant_quotes) / len(relevant_quotes)
        return None

    def _month_code_to_number(self, month_code: str) -> int:
        """Convert month code to number (1-12)"""
        month_map = {
            'F': 1,  # January
            'G': 2,  # February
            'H': 3,  # March
            'J': 4,  # April
            'K': 5,  # May
            'M': 6,  # June
            'N': 7,  # July
            'Q': 8,  # August
            'U': 9,  # September
            'V': 10, # October
            'X': 11, # November
            'Z': 12  # December
        }
        return month_map.get(month_code, 1)

    def _get_initial_price(self, commodity: str) -> float:
        """Get initial price for a contract based on commodity"""
        default_prices = {
            # Grains
            "CORN": 215,
            "WHEAT": 230,
            "SOYBEAN": 380,
            
            # Softs
            "SUGAR": 19.54,
            "COFFEE": 328.60,
            "COTTON": 68.78,
            
            # Energy
            "WEST TEXAS OIL": 70.17,
            "BRENT OIL": 73.84,
            "NATURAL GAS": 3.522,
            
            # Currencies
            "EURUSD": 1.09234,
            "GBPUSD": 1.25223,
            "USDJPY": 155.725,
            
            # Financials
            "10YR TREASURY": 108.515625,
            "5YR TREASURY": 106.06875
        }
        return default_prices.get(commodity, 100.0)

    def place_order(self, order: FuturesOrder) -> bool:
        """Place a new futures order"""
        # Validate order
        if not self._validate_order(order):
            return False
            
        # Calculate margin requirement
        contract = self.active_contracts[order.contract_id]
        margin_required = (
            abs(order.quantity) * 
            contract.price * 
            contract.spec.contract_size * 
            contract.spec.initial_margin_pct
        )
        
        # Check available capital
        if margin_required > self.game.capital:
            self.game.flash_message("Insufficient capital for margin requirement!", 13)
            return False
        
        # For market orders, execute immediately
        if order.order_type == OrderType.MARKET:
            return self._execute_order(order)
        
        # For limit orders, add to order book
        self.orders.append(order)
        return True
    
    def _validate_order(self, order: FuturesOrder) -> bool:
        """Validate order parameters"""
        if order.contract_id not in self.active_contracts:
            return False
            
        if order.quantity <= 0:
            return False
            
        if order.order_type == OrderType.LIMIT and not order.price:
            return False
            
        return True
    
    def _calculate_margin_requirement(self, contract: FuturesContract, quantity: int, price: float) -> float:
        """Calculate initial margin requirement with proper conversions"""
        contract_value = self._calculate_contract_value(contract, quantity, price)
        margin_required = contract_value * contract.spec.initial_margin_pct
        return margin_required

    def _execute_order(self, order: FuturesOrder) -> bool:
        """Execute order with correct margin handling"""
        contract = self.active_contracts[order.contract_id]
        
        # Determine execution price based on order side
        if order.side == OrderSide.BUY:
            fill_price = contract.ask
        else:
            fill_price = contract.bid
        
        # Calculate margin requirement
        margin_required = self._calculate_margin_requirement(
            contract, 
            order.quantity,
            fill_price
        )
        
        # Check capital
        if margin_required > self.game.capital:
            self.game.flash_message(f"Need ${self.game._format_number(margin_required, 0)} margin available!", 13)
            return False
            
        # Calculate contract value (for P&L purposes)
        contract_value = self._calculate_contract_value(
            contract,
            order.quantity,
            fill_price
        )
        
        position_key = (order.contract_id, order.position_type)
        existing_position = self.positions.get(position_key)
        
        if existing_position:
            # Update existing position
            new_quantity = order.quantity if order.side == OrderSide.BUY else -order.quantity
            
            if (existing_position.quantity > 0 and new_quantity < 0) or \
            (existing_position.quantity < 0 and new_quantity > 0):
                # Closing trade - calculate realized P&L
                closing_quantity = min(abs(existing_position.quantity), abs(new_quantity))
                price_diff = fill_price - existing_position.average_price
                
                # For closing trades:
                # If we're long (quantity > 0), we're selling at bid
                # If we're short (quantity < 0), we're buying at ask
                if existing_position.quantity > 0:
                    # Selling long position at bid
                    realized_pnl = closing_quantity * (contract.bid - existing_position.average_price)
                else:
                    # Buying back short position at ask
                    realized_pnl = closing_quantity * (existing_position.average_price - contract.ask)
                
                realized_pnl *= contract.spec.contract_size
                
                # Update position and capital
                existing_position.realized_pnl += realized_pnl
                self.game.capital += realized_pnl
                
                # Release margin proportionally
                margin_released = closing_quantity / abs(existing_position.quantity) * existing_position.margin_held
                self.game.capital += margin_released
                self.total_margin_required -= margin_released
                existing_position.margin_held -= margin_released
                
                # Update position size
                remaining_quantity = existing_position.quantity + new_quantity
                if remaining_quantity == 0:
                    # Position fully closed
                    del self.positions[position_key]
                    self.game.flash_message(
                        f"Position closed - P&L: ${self.game._format_number(realized_pnl, 0)}", 
                        4 if realized_pnl > 0 else 3
                    )
                else:
                    # Position partially closed
                    existing_position.quantity = remaining_quantity
            else:
                # Adding to position - calculate new average price
                total_quantity = existing_position.quantity + new_quantity
                if abs(new_quantity) > abs(existing_position.quantity):
                    # If new trade is larger, use new price
                    existing_position.average_price = fill_price
                else:
                    # Otherwise keep existing average
                    existing_position.average_price = existing_position.average_price
                    
                existing_position.quantity = total_quantity
                
                # Add new margin requirement
                existing_position.margin_held += margin_required
                self.game.capital -= margin_required
                self.total_margin_required += margin_required
        else:
            # Create new position
            self.positions[position_key] = FuturesPosition(
                contract_id=order.contract_id,
                quantity=order.quantity if order.side == OrderSide.BUY else -order.quantity,
                average_price=fill_price,
                position_type=order.position_type,
                spec=contract.spec,
                margin_held=margin_required
            )
            
            # Deduct initial margin
            self.game.capital -= margin_required
            self.total_margin_required += margin_required
        
        # Update contract statistics
        contract.volume += abs(order.quantity)
        #contract.open_interest += abs(order.quantity)
        
        # Flash execution message
        side_text = "BOT" if order.side == OrderSide.BUY else "SLD"
        self.game.flash_message(
            f"{side_text} {order.quantity} {contract.spec.name} @ {self.game._format_number(fill_price, 2)}", 
            4 if order.side == OrderSide.BUY else 3
        )
        
        return True
    
    def update_positions(self):
        """Update contract prices and positions with proper roll handling"""
        if self.game.market.current_week == self._last_update_week:
            return
            
        self._last_update_week = self.game.market.current_week
        current_week = self.game.market.current_week
        current_year = self.game.market.year

        # Track contracts that need rolling
        contracts_to_roll = {}
        
        # Group existing contracts by commodity
        contracts_by_commodity = {}
        for contract_id, contract in self.active_contracts.items():
            if contract.spec.name not in contracts_by_commodity:
                contracts_by_commodity[contract.spec.name] = []
            contracts_by_commodity[contract.spec.name].append(contract)

        # First pass: identify contracts needing to roll
        for contract_id, contract in list(self.active_contracts.items()):
            weeks_to_expiry = (contract.expiry_week - current_week) + \
                            ((contract.expiry_year - current_year) * 52)
            
            if weeks_to_expiry <= 0:
                # Find or create the next contract for this commodity
                next_contract = self._get_next_contract(contract.spec)
                if next_contract:
                    contracts_to_roll[contract_id] = next_contract.contract_id

                # Check if we need to create a new forward contract
                commodity_contracts = contracts_by_commodity.get(contract.spec.name, [])
                if len(commodity_contracts) <= 4:  # If we're at or below desired number of contracts
                    # Create a new contract only for this specific commodity
                    self.create_contracts_for_spec(contract.spec)

        # Handle rolls and position transfers
        for old_contract_id, new_contract_id in contracts_to_roll.items():
            old_contract = self.active_contracts[old_contract_id]
            
            # Roll any positions in this contract
            position_key = (old_contract_id, PositionType.SPECULATIVE)
            if position_key in self.positions:
                position = self.positions[position_key]
                self._roll_position(position, new_contract_id)
            
            # Update UI selection if needed
            if hasattr(self.game, 'futures_ui') and self.game.futures_ui.selected_contract_id == old_contract_id:
                self.game.futures_ui.selected_contract_id = new_contract_id
            
            # Remove expired contract
            del self.active_contracts[old_contract_id]
            self.game.flash_message(f"{old_contract_id} rolled to {new_contract_id}", 6)

        # Update remaining contract prices
        for contract in self.active_contracts.values():
            volatility = self._get_asset_class_volatility(contract.spec.asset_class)
            base_change = random.gauss(0, volatility)
            reference_price = self._get_reference_price(contract)
            
            if reference_price is not None:
                weeks_to_expiry = (contract.expiry_week - current_week) + \
                                ((contract.expiry_year - current_year) * 52)
                new_price = self._calculate_new_price(contract, reference_price, base_change, weeks_to_expiry)
                contract.update_price(round(new_price, 2))

        # Update position P&L
        for position in self.positions.values():
            if position.contract_id in self.active_contracts:
                contract = self.active_contracts[position.contract_id]
                position.update_pnl(contract.price)

    def _get_asset_class_volatility(self, asset_class: AssetClass) -> float:
        """Get base volatility for each asset class"""
        volatilities = {
            AssetClass.AGRICULTURE: 0.01,  # 1.5% - grains relatively stable
            AssetClass.SOFTS: 0.01,        # 2.5% - more volatile
            AssetClass.ENERGY: 0.015,        # 3.0% - highly volatile
            AssetClass.CURRENCY: 0.02,     # 0.8% - relatively stable
            AssetClass.FINANCIAL: 0.01     # 1.2% - moderate volatility
        }
        return volatilities.get(asset_class, 0.015)

    def _get_reference_price(self, contract: FuturesContract) -> Optional[float]:
        """Get reference price for price calculations"""
        if contract.spec.asset_class == AssetClass.AGRICULTURE:
            # Use physical market price for grains
            return self._get_physical_price(contract.spec.name)
            
        elif contract.spec.asset_class == AssetClass.ENERGY:
            # Energy contracts reference each other
            if contract.spec.name == "BRENT OIL":
                base = self._get_initial_price("BRENT OIL")
                return base * (1 + random.gauss(0, 0.02))  # More volatile
            elif contract.spec.name == "WEST TEXAS OIL":
                # WTI typically trades at discount to Brent
                brent_price = self._get_initial_price("BRENT OIL")
                return brent_price * 0.95 * (1 + random.gauss(0, 0.02))
                
        elif contract.spec.asset_class == AssetClass.CURRENCY:
            # Use base FX rates with small adjustments
            return self._get_initial_price(contract.spec.name)
            
        elif contract.spec.asset_class == AssetClass.FINANCIAL:
            # Treasury futures move inverse to rates
            if "TREASURY" in contract.spec.name:
                rate_change = random.gauss(0, 0.001)  # 0.1% rate volatility
                return contract.price * (1 - rate_change * 10)  # Price moves opposite to rates
                
        return contract.price  # Fallback to current price

    def _calculate_new_price(self, contract: FuturesContract, 
                            reference_price: float, base_change: float, 
                            weeks_to_expiry: int) -> float:
        """Calculate new price considering asset class characteristics"""
        # Start with reference price
        new_price = contract.price
        
        # Calculate carry cost based on asset class
        carry_cost = 0
        if contract.spec.asset_class == AssetClass.AGRICULTURE:
            carry_cost = 0.001 * weeks_to_expiry  # Storage costs
        elif contract.spec.asset_class == AssetClass.ENERGY:
            carry_cost = 0.002 * weeks_to_expiry  # Higher storage/financing
        elif contract.spec.asset_class == AssetClass.SOFTS:
            carry_cost = 0.0015 * weeks_to_expiry  # Moderate storage costs
            
        # Mean reversion to reference price
        basis = contract.price - reference_price
        mean_reversion = -basis * 0.1  # 10% mean reversion
        
        # Combine all factors
        total_change = base_change + carry_cost + mean_reversion
        
        # Apply price change with limits
        max_change = 0.03  # 3% limit per update
        new_price = contract.price * (1 + min(max_change, max(-max_change, total_change)))
        
        return new_price
    
    def _is_expiring(self, contract_id: str) -> bool:
        """Check if contract is expiring this week"""
        # Implementation depends on exact expiration rules
        return False
    
    def _handle_expiration(self, position: FuturesPosition):
        """Handle expiring futures position with proper P&L settlement"""
        contract = self.active_contracts[position.contract_id]
        
        # Calculate final P&L at settlement
        final_pnl = position.unrealized_pnl
        self.game.capital += final_pnl
        
        # Release margin
        self.game.capital += position.margin_held
        self.total_margin_required -= position.margin_held
        
        # Clean up the position
        position_key = (position.contract_id, position.position_type)
        del self.positions[position_key]
        
        # Notify user
        self.game.flash_message(
            f"Position in {contract.spec.name} expired - P&L: ${self.game._format_number(final_pnl, 0)}", 
            4 if final_pnl > 0 else 3
        )

    def _get_next_contract(self, spec: ContractSpecification) -> Optional[FuturesContract]:
        """Get or create the next available contract for rolling"""
        current_week = self.game.market.current_week
        current_year = self.game.market.year
        
        # Find the next valid expiry week
        valid_expiries = []
        for weeks_forward in spec.weeks_to_expiry:
            expiry_week = current_week + weeks_forward
            expiry_year = current_year
            
            while expiry_week > 52:
                expiry_week -= 52
                expiry_year += 1
                
            valid_expiries.append((expiry_week, expiry_year))
        
        # Sort by date
        valid_expiries.sort(key=lambda x: (x[1], x[0]))
        
        # Find first expiry that's after current date
        for expiry_week, expiry_year in valid_expiries:
            if expiry_year > current_year or (expiry_year == current_year and expiry_week > current_week):
                contract_id = f"{spec.name}W{expiry_week}-{expiry_year}"
                
                # Create contract if it doesn't exist
                if contract_id not in self.active_contracts:
                    self.create_contracts_for_spec(spec)
                
                if contract_id in self.active_contracts:
                    return self.active_contracts[contract_id]
        
        return None

    def _roll_position(self, position: FuturesPosition, new_contract_id: str):
        """Roll a position to a new contract"""
        if new_contract_id not in self.active_contracts:
            return
            
        new_contract = self.active_contracts[new_contract_id]
        old_contract_id = position.contract_id
        
        # Create new position with same quantity
        new_position = FuturesPosition(
            contract_id=new_contract_id,
            quantity=position.quantity,
            average_price=new_contract.price,
            position_type=position.position_type,
            spec=new_contract.spec,
            margin_held=position.margin_held
        )
        
        # Store new position
        new_key = (new_contract_id, position.position_type)
        self.positions[new_key] = new_position
        
        # Remove old position
        old_key = (old_contract_id, position.position_type)
        del self.positions[old_key]

    def _format_contract_size(self, contract: FuturesContract) -> str:
        """Format contract size display based on asset class"""
        if contract.spec.asset_class == AssetClass.AGRICULTURE:
            return f"Size: {contract.spec.contract_size:,} Metric Tons"
            
        elif contract.spec.asset_class == AssetClass.SOFTS:
            if contract.spec.name == "SUGAR":
                return f"Size: {contract.spec.contract_size:,} lbs ({contract.spec.contract_size / 2204.62:.0f} MT)"
            elif contract.spec.name == "COFFEE":
                return f"Size: {contract.spec.contract_size:,} lbs ({contract.spec.contract_size / 2204.62:.0f} MT)"
            elif contract.spec.name == "COTTON":
                return f"Size: {contract.spec.contract_size:,} lbs ({contract.spec.contract_size / 2204.62:.0f} MT)"
                
        elif contract.spec.asset_class == AssetClass.ENERGY:
            if contract.spec.name == "NATURAL GAS":
                return f"Size: {contract.spec.contract_size:,} MMBtu"
            else:
                return f"Size: {contract.spec.contract_size:,} Barrels"
                
        elif contract.spec.asset_class == AssetClass.CURRENCY:
            currency_symbols = {
                "EURUSD": "€",
                "GBPUSD": "£",
                "USDJPY": "¥"
            }
            symbol = currency_symbols.get(contract.spec.currency, "$")
            if contract.spec.name == "USDJPY":
                return f"Size: ¥{contract.spec.contract_size:,}"
            else:
                return f"Size: {symbol}{contract.spec.contract_size:,}"
                
        elif contract.spec.asset_class == AssetClass.FINANCIAL:
            return f"Face Value: ${contract.spec.contract_size:,}"
            
        return f"Size: {contract.spec.contract_size:,}"

    def _format_contract_price(self, contract: FuturesContract, price: float) -> str:
        """Format price display based on contract type and specifications"""
        if price is None:
            return "N/A"

        # Currency pairs need special handling
        if contract.spec.name == "EURUSD" or contract.spec.name == "GBPUSD":
            return f"{price:.5f}"  # 5 decimal places for major FX
        elif contract.spec.name == "USDJPY":
            return f"{price:.3f}"  # 3 decimal places for JPY
            
        # Softs are quoted in cents/lb
        elif contract.spec.asset_class == AssetClass.SOFTS:
            if contract.spec.name == "COFFEE":
                return f"{price:.2f}"  # Coffee typically shown with 2 decimals
            return f"{price:.2f}"      # Sugar and Cotton with 2 decimals

        # Treasuries use fractional display
        elif contract.spec.asset_class == AssetClass.FINANCIAL:
            points = int(price)
            ticks = round((price - points) * 32)  # Convert decimal to 32nds
            return f"{points}'{ticks:02d}"        # Format as 108'16 for 108.5

        # Agricultural products use 2 decimal places
        elif contract.spec.asset_class == AssetClass.AGRICULTURE:
            return f"{price:.2f}"

        # Default formatting
        return f"{price:.2f}"

    def _calculate_contract_value(self, contract: FuturesContract, quantity: int, price: float) -> float:
        """Calculate full contract value with proper units"""
        if contract.spec.asset_class == AssetClass.SOFTS:
            # Convert cents/lb to dollars and multiply by contract size
            return (price / 100.0) * contract.spec.contract_size * quantity
        elif contract.spec.asset_class == AssetClass.FINANCIAL:
            # Treasury futures are quoted in points where 1 point = $1,000
            return price * 1000 * quantity
        else:
            return price * contract.spec.contract_size * quantity

class FuturesUI:
    """Manages the futures trading interface"""
    def __init__(self, game):
        self.game = game
        self.active_tab = AssetClass.AGRICULTURE
        self.selected_contract_id = None
        self.order_type = OrderType.MARKET
        self.order_quantity = 0
        self.order_price = 0.0
        self.show_depth = True
        self.scroll_offset = 0
        self.quantity_multipliers = [1, 5, 10, 50, 100]  # Define available multipliers
        self.current_multiplier_index = 0  # Track current multiplier
        self.quantity_multiplier = self.quantity_multipliers[0]
        self.futures_graph = FuturesCurveGraph()
        
    def draw(self):
        """Draw the futures trading interface"""
        # Draw main panel
        self.game.draw_panel(5, 30, 440, 380, "FUTURES TRADING")
        
        # Draw asset class tabs
        self._draw_asset_tabs(10, 40)
        
        # Draw contract chain
        self._draw_contract_chain(10, 60, 280, 150)
        
        # Draw order entry
        self._draw_order_entry(295, 60, 145, 150)
        
        # Draw positions
        self._draw_positions(10, 220, 280, 150)
        
        # Draw margin summary
        self._draw_margin_summary(295, 220, 145, 150)
        
        # Draw futures graph if visible
        self.futures_graph.update()
        self.futures_graph.draw()
    
    def _draw_asset_tabs(self, x: int, y: int):
        """Draw asset class selection tabs"""
        tab_width = 70
        
        for i, asset_class in enumerate(AssetClass):
            tab_x = x + (i * tab_width)
            selected = asset_class == self.active_tab
            self.game.draw_panel(tab_x, y, tab_width-1, 15, "")
            pyxel.rect(tab_x, y, tab_width-1, 15, 2 if selected else 1)
            pyxel.text(tab_x+5, y+5, asset_class.value, 7 if selected else 8)
    
    def _draw_contract_chain(self, x: int, y: int, w: int, h: int):
        """Draw the contract chain grid with bid/offer prices"""
        # Draw the main panel container
        self.game.draw_panel(x, y, w, h, "CONTRACT CHAIN")

        # Draw column headers
        headers = ["Contract", "Expiry", "Bid", "Offer", "Change"]
        header_x = [x+10, x+76, x+130, x+180, x+230]
        for header, hx in zip(headers, header_x):
            pyxel.text(hx, y+15, header, 8)

        # Filter contracts for current asset class
        visible_contracts = [
            contract for contract in self.game.futures_manager.active_contracts.values()
            if contract.spec.asset_class == self.active_tab
        ]

        # Create groups by commodity
        contract_groups = {}
        for contract in visible_contracts:
            if contract.spec.name not in contract_groups:
                contract_groups[contract.spec.name] = []
            contract_groups[contract.spec.name].append(contract)
        
        # Sort contracts within each group by expiry
        for commodity in contract_groups:
            contract_groups[commodity].sort(key=lambda c: (c.expiry_year, c.expiry_week))

        # Draw contract rows
        row_y = y + 30
        visible_rows = (h - 40) // 10
        rows_drawn = 0

        # Use predefined commodity order for consistent navigation
        commodity_order = {
            AssetClass.AGRICULTURE: ["CORN", "WHEAT", "SOYBEAN"],
            AssetClass.SOFTS: ["SUGAR", "COFFEE", "COTTON"],
            AssetClass.ENERGY: ["WEST TEXAS OIL", "BRENT OIL", "NATURAL GAS"],
            AssetClass.CURRENCY: ["EURUSD", "GBPUSD", "USDJPY"],
            AssetClass.FINANCIAL: ["10YR TREASURY", "5YR TREASURY"]
        }

        ordered_commodities = commodity_order.get(self.active_tab, [])

        for commodity in ordered_commodities:
            if commodity not in contract_groups:
                continue

            for contract in contract_groups[commodity]:
                if rows_drawn >= self.scroll_offset and rows_drawn < self.scroll_offset + visible_rows:
                    # Highlight selected contract
                    if contract.contract_id == self.selected_contract_id:
                        pyxel.rect(x+5, row_y-1, w-10, 9, 2)
                    
                    # Format prices based on contract type
                    if contract.spec.name in ["EURUSD", "GBPUSD"]:
                        bid_str = f"{contract.bid:.5f}"
                        ask_str = f"{contract.ask:.5f}"
                        change_str = f"{(contract.price - contract.last_price):.5f}"
                    elif contract.spec.name == ["USDJPY", "NATURAL GAS"]:
                        bid_str = f"{contract.bid:.3f}"
                        ask_str = f"{contract.ask:.3f}"
                        change_str = f"{(contract.price - contract.last_price):.3f}"
                    elif contract.spec.asset_class == AssetClass.FINANCIAL:
                        # Format Treasury prices in points and ticks
                        bid_points = int(contract.bid)
                        bid_ticks = round((contract.bid - bid_points) * 32)
                        ask_points = int(contract.ask)
                        ask_ticks = round((contract.ask - ask_points) * 32)
                        change_points = int(contract.price - contract.last_price)
                        change_ticks = round(((contract.price - contract.last_price) - change_points) * 32)
                        bid_str = f"{bid_points}'{bid_ticks:02d}"
                        ask_str = f"{ask_points}'{ask_ticks:02d}"
                        change_str = f"{change_points}'{change_ticks:02d}"
                    else:
                        # Agriculture and Softs use 2 decimal places
                        bid_str = f"{contract.bid:.2f}"
                        ask_str = f"{contract.ask:.2f}"
                        change_str = f"{(contract.price - contract.last_price):.2f}"
                    
                    # Draw contract details
                    price_color = 4 if contract.price > contract.last_price else 3 if contract.price < contract.last_price else 7
                    
                    pyxel.text(header_x[0], row_y, f"{contract.spec.name}", 7)
                    pyxel.text(header_x[1], row_y, f"W{contract.expiry_week}-{contract.expiry_year}", 7)
                    pyxel.text(header_x[2], row_y, bid_str, 3)  # Bid in red
                    pyxel.text(header_x[3], row_y, ask_str, 4)  # Offer in green
                    pyxel.text(header_x[4], row_y, change_str, price_color)
                
                row_y += 10
                rows_drawn += 1

        # Draw scrollbar if needed
        if rows_drawn > visible_rows:
            self.game.draw_scrollbar(x+w-5, y+20, h-25, rows_drawn, visible_rows)
    
    def _draw_order_entry(self, x: int, y: int, w: int, h: int):
        """Draw the order entry panel with optimized layout"""
        self.game.draw_panel(x, y, w, h, "ORDER ENTRY")
        
        # Validate selected contract
        if self.selected_contract_id not in self.game.futures_manager.active_contracts:
            if self.selected_contract_id:
                commodity = self.selected_contract_id.split('W')[0]
                for contract_id in self.game.futures_manager.active_contracts:
                    if contract_id.startswith(commodity):
                        self.selected_contract_id = contract_id
                        break
                else:
                    self.selected_contract_id = None

        if not self.selected_contract_id:
            pyxel.text(x+20, y+30, "Select Contract", 8)
            return
            
        try:
            contract = self.game.futures_manager.active_contracts[self.selected_contract_id]
            
            # Draw contract info
            y_pos = y + 15
            pyxel.text(x+10, y_pos, f"Contract: {contract.spec.name}W{contract.expiry_week}", 7)
            
            # Show contract specifications
            y_pos += 12
            pyxel.text(x+10, y_pos, f"Size: {contract.spec.contract_size:,} {contract.spec.unit}", 8)
            
            # Draw quantity controls with multiplier
            y_pos += 15
            quantity_text = f"Quantity: {self.order_quantity}"
            if self.quantity_multiplier > 1:
                quantity_text += f" (x{self.quantity_multiplier})"
            pyxel.text(x+10, y_pos, quantity_text, 7)
            
            # Calculate and display total contract value
            y_pos += 15
            total_size = self.order_quantity * contract.spec.contract_size
            total_value = total_size * contract.price
            pyxel.text(x+10, y_pos, f"Value: ${self.game._format_number(total_value, 0)}", 7)
            
            # Calculate and display margin requirement
            if self.order_quantity > 0:
                y_pos += 15
                margin_required = (
                    self.order_quantity * 
                    contract.price * 
                    contract.spec.contract_size * 
                    contract.spec.initial_margin_pct
                )
                margin_color = 4 if margin_required <= self.game.capital else 3
                pyxel.text(x+10, y_pos, f"Margin: ${self.game._format_number(margin_required, 0)}", margin_color)
                
                # Show available capital after margin
                y_pos += 12
                remaining_capital = self.game.capital - margin_required
                capital_color = 4 if remaining_capital > 0 else 3
                pyxel.text(x+10, y_pos, f"Remain: ${self.game._format_number(remaining_capital, 0)}", capital_color)
            
            # Order type and price display
            y_pos += 15
            order_type_color = 10 if self.order_type == OrderType.MARKET else 7
            price_text = "MARKET" if self.order_type == OrderType.MARKET else f"${self.game._format_number(self.order_price, 3)}"
            pyxel.text(x+10, y_pos, f"{price_text}", order_type_color)
            
            # Show bid/ask inline
            pyxel.text(x+70, y_pos, f"B: ${self.game._format_number(contract.bid, 2)}", 3)
            pyxel.text(x+70, y_pos+10, f"A: ${self.game._format_number(contract.ask, 2)}", 4)
            
            # Draw action buttons
            y_pos += 25  # Adjusted spacing
            button_width = 50
            
            # Buy button - green if we can afford margin
            buy_enabled = margin_required <= self.game.capital if self.order_quantity > 0 else False
            buy_color = 4 if buy_enabled else 1
            pyxel.rect(x+10, y_pos, button_width, 12, buy_color)
            pyxel.text(x+25, y_pos+2, "BUY", 7)
            
            # Sell button - red if we can afford margin
            sell_color = 3 if buy_enabled else 1
            pyxel.rect(x+70, y_pos, button_width, 12, sell_color)
            pyxel.text(x+85, y_pos+2, "SELL", 7)
            
        except KeyError:
            self.selected_contract_id = None
            pyxel.text(x+20, y+30, "Select Contract", 8)
    
    def _draw_positions(self, x: int, y: int, w: int, h: int):
        """Draw the positions panel showing only active positions"""
        self.game.draw_panel(x, y, w, h, "YOUR POSITIONS")

        # Draw headers
        headers = ["Contract", "Qty", "Avg Price", "P&L", "Value", "Type"]
        header_x = [x+10, x+70, x+120, x+180, x+240, x+300]
        for header, hx in zip(headers, header_x):
            pyxel.text(hx, y+15, header, 8)
        
        # Filter and sort positions - only show active positions
        active_positions = [
            (key, pos) for key, pos in self.game.futures_manager.positions.items()
            if pos.quantity != 0  # Filter out closed positions
        ]
        
        if not active_positions:
            pyxel.text(x+50, y+50, "NO ACTIVE POSITIONS", 8)
            return
            
        # Draw positions
        row_y = y + 30
        for (contract_id, position_type), position in active_positions:
            contract = self.game.futures_manager.active_contracts[contract_id]
            
            # Calculate position value including contract size
            position_value = abs(position.quantity) * \
                           position.average_price * \
                           contract.spec.contract_size
            
            # Determine colors
            pnl_color = 4 if position.unrealized_pnl > 0 else 3
            type_color = 6 if position_type == PositionType.HEDGE else 7
            qty_color = 4 if position.quantity > 0 else 3
            
            # Draw position details
            pyxel.text(header_x[0], row_y, f"{contract.spec.name}W{contract.expiry_week}", 7)
            pyxel.text(header_x[1], row_y, str(position.quantity), qty_color)
            pyxel.text(header_x[2], row_y, self.game._format_number(position.average_price, 2), 7)
            pyxel.text(header_x[3], row_y, self.game._format_number(position.unrealized_pnl, 0), pnl_color)
            pyxel.text(header_x[4], row_y, self.game._format_number(position_value, 0), 7)
            pyxel.text(header_x[5], row_y, position_type.value[:4], type_color)
            
            row_y += 10
            
        # Show total P&L
        total_pnl = sum(pos.unrealized_pnl for _, pos in active_positions)
        total_margin = sum(pos.margin_held for _, pos in active_positions)
        
        # Draw summary at bottom
        summary_y = y + h - 25
        pyxel.text(x+10, summary_y, f"Total P&L: ${self.game._format_number(total_pnl, 0)}", 
                  4 if total_pnl > 0 else 3)
        pyxel.text(x+10, summary_y+10, f"Margin Held: ${self.game._format_number(total_margin, 0)}", 6)  
        
    def _draw_margin_summary(self, x: int, y: int, w: int, h: int):
        """Draw the margin and risk summary"""
        self.game.draw_panel(x, y, w, h, "MARGIN SUMMARY")
        
        y_pos = y + 20
        
        # Total margin required
        margin_required = self.game.futures_manager.total_margin_required
        pyxel.text(x+10, y_pos, "Required Margin:", 8)
        y_pos += 10
        pyxel.text(x+10, y_pos, f"${self.game._format_number(margin_required, 0)}", 7)
        
        # Available capital
        y_pos += 20
        pyxel.text(x+10, y_pos, "Available Capital:", 8)
        y_pos += 10
        pyxel.text(x+10, y_pos, f"${self.game._format_number(self.game.capital, 0)}", 7)
        
        # Total P&L
        y_pos += 20
        total_pnl = sum(p.unrealized_pnl for p in self.game.futures_manager.positions.values())
        pnl_color = 4 if total_pnl > 0 else 3
        pyxel.text(x+10, y_pos, "Total P&L:", 8)
        y_pos += 10
        pyxel.text(x+10, y_pos, f"${self.game._format_number(total_pnl, 0)}", pnl_color)
    
    def handle_input(self):
        """Handle futures trading interface input"""
        # Asset class navigation with F key (for Futures type)
        if pyxel.btnp(pyxel.KEY_F):
            asset_classes = list(AssetClass)
            current_idx = asset_classes.index(self.active_tab)
            self.active_tab = asset_classes[(current_idx + 1) % len(asset_classes)]
            self.selected_contract_id = None
            self.scroll_offset = 0
        
        # Contract selection
        if pyxel.btnp(pyxel.KEY_UP):
            self._move_selection(-1)
        elif pyxel.btnp(pyxel.KEY_DOWN):
            self._move_selection(1)
        
        if pyxel.btnp(pyxel.KEY_X):
            self.current_multiplier_index = (self.current_multiplier_index + 1) % len(self.quantity_multipliers)
            self.quantity_multiplier = self.quantity_multipliers[self.current_multiplier_index]
            self.game.flash_message(f"Lot size multiplier: x{self.quantity_multiplier}", 4)
            
        # Handle quantity changes with new multiplier
        if self.selected_contract_id:
            if pyxel.btnp(pyxel.KEY_LEFT):
                self.order_quantity = max(0, self.order_quantity - self.quantity_multiplier)
            elif pyxel.btnp(pyxel.KEY_RIGHT):
                self.order_quantity += self.quantity_multiplier
            
            # Execute orders
            if pyxel.btnp(pyxel.KEY_B):
                self._submit_order(OrderSide.BUY)
            elif pyxel.btnp(pyxel.KEY_S):
                self._submit_order(OrderSide.SELL)
        
        if pyxel.btnp(pyxel.KEY_G):
            if self.selected_contract_id:
                contract = self.game.futures_manager.active_contracts[self.selected_contract_id]
                # Get all contracts for this commodity
                commodity_contracts = [
                    c for c in self.game.futures_manager.active_contracts.values()
                    if c.spec.name == contract.spec.name
                ]
                print(commodity_contracts)
                # Sort contracts by expiry
                commodity_contracts.sort(key=lambda c: (c.expiry_year, c.expiry_week))
                if not self.futures_graph.show(contract.spec.name, commodity_contracts):
                    self.game.flash_message("No contracts available for graph", 6)
    
    def _move_selection(self, direction: int):
        """Move contract selection with validation"""
        # First, organize contracts by commodity in our desired order
        commodity_order = {
            AssetClass.AGRICULTURE: ["CORN", "WHEAT", "SOYBEAN"],
            AssetClass.SOFTS: ["SUGAR", "COFFEE", "COTTON"],
            AssetClass.ENERGY: ["WEST TEXAS OIL", "BRENT OIL", "NATURAL GAS"],
            AssetClass.CURRENCY: ["EURUSD", "GBPUSD", "USDJPY"],
            AssetClass.FINANCIAL: ["10YR TREASURY", "5YR TREASURY"]
        }
        
        # Get ordered commodities for current asset class
        ordered_commodities = commodity_order.get(self.active_tab, [])
        
        # Create ordered list of contracts following our commodity order
        ordered_contracts = []
        for commodity in ordered_commodities:
            commodity_contracts = [
                contract for contract in self.game.futures_manager.active_contracts.values()
                if contract.spec.asset_class == self.active_tab and contract.spec.name == commodity
            ]
            # Sort contracts of same commodity by expiry
            commodity_contracts.sort(key=lambda c: (c.expiry_year, c.expiry_week))
            ordered_contracts.extend(commodity_contracts)
        
        if not ordered_contracts:
            self.selected_contract_id = None
            return
            
        if self.selected_contract_id is None:
            self.selected_contract_id = ordered_contracts[0].contract_id
            return
            
        # Find current position in ordered list
        current_idx = next(
            (i for i, c in enumerate(ordered_contracts) 
            if c.contract_id == self.selected_contract_id),
            0
        )
        
        # Move selection
        new_idx = (current_idx + direction) % len(ordered_contracts)
        self.selected_contract_id = ordered_contracts[new_idx].contract_id
    
    def _submit_order(self, side: OrderSide):
        """Submit a futures order"""
        if not self.selected_contract_id or self.order_quantity <= 0:
            return
            
        order = FuturesOrder(
            contract_id=self.selected_contract_id,
            order_type=self.order_type,
            side=side,
            quantity=self.order_quantity,
            price=self.order_price if self.order_type == OrderType.LIMIT else None,
            position_type=PositionType.SPECULATIVE
        )
        
        if self.game.futures_manager.place_order(order):
            self.game.flash_message(
                f"{side.value} {self.order_quantity} {self.selected_contract_id} @ "
                f"{'MARKET' if self.order_type == OrderType.MARKET else self.order_price}",
                4 if side == OrderSide.BUY else 3
            )
            self.order_quantity = 0
            self.order_price = 0.0


class FuturesCurveGraph:
    def __init__(self):
        self.visible = False
        self.animation_progress = 0.0
        self.current_commodity = None
        self.contracts = []
        self.min_price = float('inf')
        self.max_price = float('-inf')
        
    def show(self, commodity: str, contracts: List[FuturesContract]) -> bool:
        """Show graph for a specific commodity's contracts"""
        if not contracts:
            return False
            
        # Reset price range for new graph
        self.min_price = float('inf')
        self.max_price = float('-inf')
            
        self.visible = True
        self.animation_progress = 0.0
        self.current_commodity = commodity
        
        # Sort contracts by expiry
        self.contracts = sorted(contracts, 
                            key=lambda x: (x.expiry_year, x.expiry_week))
        
        # Calculate price range including padding
        for contract in self.contracts:
            mid_price = (contract.bid + contract.ask) / 2
            self.min_price = min(self.min_price, mid_price * 0.995)
            self.max_price = max(self.max_price, mid_price * 1.005)
        
        return True
        
    def hide(self):
        """Hide the graph"""
        self.visible = False
        
    def update(self):
        """Update animation state"""
        if not self.visible:
            self.animation_progress = max(0.0, self.animation_progress - 0.1)  # Slowed down fade out
            return
            
        self.animation_progress = min(1.0, self.animation_progress + 0.1)  # Slowed down fade in
        
        if pyxel.btnp(pyxel.KEY_X):
            self.hide()
            
    def draw(self):
        """Draw the forward curve visualization"""
        if not self.visible or self.animation_progress <= 0 or not self.contracts:  # Added contracts check
            return
            
        # Calculate window dimensions with animation
        window_width = 300
        window_height = 200
        x = (450 - window_width) // 2
        y = (450 - window_height) // 2
        
        # Apply slide-in animation
        current_y = y + (1 - self.animation_progress) * window_height
        
        # Draw window background
        pyxel.rect(x, current_y, window_width, window_height, 1)
        pyxel.rectb(x, current_y, window_width, window_height, 2)
        
        # Draw title bar
        title = f"{self.current_commodity} Forward Curve"
        title_x = x + (window_width - len(title) * 4) // 2
        pyxel.rect(x, current_y, window_width, 10, 2)
        pyxel.text(title_x, current_y + 2, title, 7)
        
        # Calculate graph dimensions
        graph_x = x + 40
        graph_y = current_y + 30
        graph_width = window_width - 60
        graph_height = window_height - 50
        
        # Draw axes
        pyxel.rectb(graph_x, graph_y, graph_width, graph_height, 5)
        
        if len(self.contracts) >= 2:
            # Calculate y-axis labels
            price_range = self.max_price - self.min_price
            num_labels = 5
            
            for i in range(num_labels):
                # Calculate price and position
                price = self.min_price + (price_range * i / (num_labels - 1))
                label_y = graph_y + graph_height - (i * graph_height / (num_labels - 1))
                
                # Format price based on commodity type
                if self.current_commodity in ["EURUSD", "GBPUSD"]:
                    price_str = f"{price:.5f}"
                elif self.current_commodity == "USDJPY":
                    price_str = f"{price:.3f}"
                else:
                    price_str = f"{price:.2f}"
                
                # Draw price label and grid line
                pyxel.text(x + 5, label_y - 2, price_str, 7)
                pyxel.line(graph_x, label_y, graph_x + graph_width, label_y, 2)
            
            # Plot points and lines
            points = []
            for i, contract in enumerate(self.contracts):
                # Calculate mid price and position
                mid_price = (contract.bid + contract.ask) / 2
                x_pos = graph_x + (i * graph_width / (len(self.contracts) - 1))
                y_pos = graph_y + graph_height - (
                    (mid_price - self.min_price) * graph_height / price_range
                )
                points.append((x_pos, y_pos))
                
                # Draw expiry label
                expiry_label = f"W{contract.expiry_week}"
                pyxel.text(x_pos - 8, graph_y + graph_height + 5, expiry_label, 7)
            
            # Draw curve
            for i in range(len(points) - 1):
                x1, y1 = points[i]
                x2, y2 = points[i + 1]
                
                # Color red if backwardated, green if contango
                curve_color = 4 if y2 < y1 else 3
                pyxel.line(x1, y1, x2, y2, curve_color)
                
            # Draw points
            for x_pos, y_pos in points:
                pyxel.circb(x_pos, y_pos, 2, 11)
                
        # Draw exit instruction
        exit_text = "PRESS X TO CLOSE"
        exit_x = x + (window_width - len(exit_text) * 4) // 2
        exit_color = 7 if (pyxel.frame_count // 15) % 2 == 0 else 5
        pyxel.text(exit_x, current_y + window_height - 15, exit_text, exit_color)


@dataclass
class CropCycle:
    """Represents a crop's planting and harvest cycle in a specific region"""
    region: str
    commodity: str
    plant_start_week: int  # Week number when planting starts
    plant_end_week: int    # Week number when planting ends
    harvest_start_week: int # Week number when harvest starts
    harvest_end_week: int   # Week number when harvest completes
    stock_peak_weeks: Tuple[int, int]  # (start_week, end_week) of peak stock period
    stock_peak_range: Tuple[float, float]  # (min%, max%) of peak stock levels
    stock_low_weeks: Tuple[int, int]  # (start_week, end_week) of low stock period
    stock_low_range: Tuple[float, float]  # (min%, max%) of low stock levels
    base_production: int  # Base annual production in MT (from WASDE)
    domestic_consumption: int  # Annual domestic use in MT (from WASDE)
    export_capacity: int  # Annual export capacity in MT (from WASDE)
    current_production: int = 0  # Current year's projected production
    harvest_progress: float = 0.0  # Progress of current harvest (0-1)
    current_stocks: int = 0  # Current stock level
    yearly_consumption: int = 0  # Annual consumption rate

class CropCycleManager:
    """Manages crop cycles and stock patterns across regions"""
    def __init__(self):
        self.cycles: Dict[Tuple[str, str], CropCycle] = {}
        self._initialize_cycles()

    def _initialize_cycles(self):
        """Initialize all crop cycles based on real-world patterns and WASDE data"""
        
        # BRAZIL
        # Split Brazil into Center-South (SANTOS/PARANAGUA) and North
        self.cycles[("BRAZIL_CS", "CORN")] = CropCycle(
            region="BRAZIL_CS",
            commodity="CORN",
            plant_start_week=40,  # October (First crop)
            plant_end_week=44,    # November
            harvest_start_week=9,  # March
            harvest_end_week=20,  # May
            stock_peak_weeks=(24, 32),  # June-August
            stock_peak_range=(0.80, 0.95),
            stock_low_weeks=(5, 8),     # February
            stock_low_range=(0.15, 0.25),
            base_production=95_000_000,  # ~76% of Brazil's 125M MT production
            domestic_consumption=37_000_000,  # ~76% of domestic consumption
            export_capacity=58_000_000,  # Based on port capacity
            yearly_consumption=37_000_000
        )

        self.cycles[("BRAZIL_CS", "SOYBEAN")] = CropCycle(
            region="BRAZIL_CS",
            commodity="SOYBEAN",
            plant_start_week=39,  # Late September
            plant_end_week=44,    # Early November
            harvest_start_week=5,  # February
            harvest_end_week=16,   # April
            stock_peak_weeks=(16, 24),  # April-June
            stock_peak_range=(0.75, 0.90),
            stock_low_weeks=(1, 4),     # January-February
            stock_low_range=(0.10, 0.20),
            base_production=129_000_000,  # Based on WASDE Brazil total 169M
            domestic_consumption=34_000_000,
            export_capacity=90_000_000,
            yearly_consumption=34_000_000
        )

        self.cycles[("BRAZIL_CS", "WHEAT")] = CropCycle(
            region="BRAZIL_CS",
            commodity="WHEAT",
            plant_start_week=16,  # April
            plant_end_week=20,    # May
            harvest_start_week=36, # September
            harvest_end_week=44,  # November
            stock_peak_weeks=(44, 52),  # Nov-Dec
            stock_peak_range=(0.70, 0.85),
            stock_low_weeks=(32, 35),   # August
            stock_low_range=(0.15, 0.25),
            base_production=28_100_000,  # From WASDE
            domestic_consumption=11_900_000,
            export_capacity=16_800_000,
            yearly_consumption=11_900_000
        )

        # ARGENTINA
        self.cycles[("ARGENTINA", "CORN")] = CropCycle(
            region="ARGENTINA",
            commodity="CORN",
            plant_start_week=36,  # September
            plant_end_week=44,    # November
            harvest_start_week=9,  # March
            harvest_end_week=24,   # June
            stock_peak_weeks=(20, 28),  # May-July
            stock_peak_range=(0.70, 0.90),
            stock_low_weeks=(5, 8),     # February-March
            stock_low_range=(0.10, 0.20),
            base_production=71_000_000,  # From WASDE
            domestic_consumption=12_300_000,
            export_capacity=58_000_000,
            yearly_consumption=12_300_000
        )

        self.cycles[("ARGENTINA", "SOYBEAN")] = CropCycle(
            region="ARGENTINA",
            commodity="SOYBEAN",
            plant_start_week=40,  # October
            plant_end_week=48,    # December
            harvest_start_week=13,  # March
            harvest_end_week=20,   # May
            stock_peak_weeks=(16, 24),  # April-June
            stock_peak_range=(0.75, 0.90),
            stock_low_weeks=(5, 8),     # February
            stock_low_range=(0.10, 0.15),
            base_production=62_000_000,  # From WASDE
            domestic_consumption=20_600_000,
            export_capacity=34_500_000,
            yearly_consumption=20_600_000
        )

        self.cycles[("ARGENTINA", "WHEAT")] = CropCycle(
            region="ARGENTINA",
            commodity="WHEAT",
            plant_start_week=20,  # May
            plant_end_week=28,    # July
            harvest_start_week=48, # December
            harvest_end_week=4,   # January
            stock_peak_weeks=(4, 12),   # Jan-March
            stock_peak_range=(0.80, 0.90),
            stock_low_weeks=(44, 47),   # November
            stock_low_range=(0.15, 0.20),
            base_production=27_500_000,  # From WASDE
            domestic_consumption=5_050_000,
            export_capacity=23_500_000,
            yearly_consumption=5_050_000
        )

        # RUSSIA
        self.cycles[("RUSSIA", "WHEAT")] = CropCycle(
            region="RUSSIA",
            commodity="WHEAT",
            plant_start_week=36,  # September (Winter)
            plant_end_week=40,    # October
            harvest_start_week=27,  # July
            harvest_end_week=32,   # August
            stock_peak_weeks=(36, 44),  # September-November
            stock_peak_range=(0.85, 0.95),
            stock_low_weeks=(23, 26),   # June
            stock_low_range=(0.15, 0.20),
            base_production=102_500_000,  # From WASDE
            domestic_consumption=34_250_000,
            export_capacity=67_000_000,
            yearly_consumption=34_250_000
        )

        self.cycles[("RUSSIA", "CORN")] = CropCycle(
            region="RUSSIA",
            commodity="CORN",
            plant_start_week=14,  # April
            plant_end_week=18,    # May
            harvest_start_week=36, # September
            harvest_end_week=44,  # November
            stock_peak_weeks=(44, 52),
            stock_peak_range=(0.80, 0.90),
            stock_low_weeks=(32, 35),
            stock_low_range=(0.15, 0.20),
            base_production=23_000_000,  # From WASDE
            domestic_consumption=5_200_000,
            export_capacity=17_300_000,
            yearly_consumption=5_200_000
        )

        self.cycles[("RUSSIA", "SOYBEAN")] = CropCycle(
            region="RUSSIA",
            commodity="SOYBEAN",
            plant_start_week=18,  # May
            plant_end_week=22,    # June
            harvest_start_week=36, # September
            harvest_end_week=44,  # November
            stock_peak_weeks=(44, 52),
            stock_peak_range=(0.75, 0.85),
            stock_low_weeks=(32, 35),
            stock_low_range=(0.15, 0.20),
            base_production=14_800_000,
            domestic_consumption=3_800_000,
            export_capacity=11_000_000,
            yearly_consumption=3_800_000
        )

        # UKRAINE
        self.cycles[("UKRAINE", "CORN")] = CropCycle(
            region="UKRAINE",
            commodity="CORN",
            plant_start_week=14,  # April
            plant_end_week=18,    # May
            harvest_start_week=36,  # September
            harvest_end_week=44,   # November
            stock_peak_weeks=(44, 52),  # November-December
            stock_peak_range=(0.80, 0.90),
            stock_low_weeks=(32, 35),   # August
            stock_low_range=(0.10, 0.15),
            base_production=36_500_000,  # From WASDE
            domestic_consumption=4_450_000,
            export_capacity=33_000_000,
            yearly_consumption=4_450_000
        )

        self.cycles[("UKRAINE", "WHEAT")] = CropCycle(
            region="UKRAINE",
            commodity="WHEAT",
            plant_start_week=36,  # September
            plant_end_week=40,    # October
            harvest_start_week=27,  # July
            harvest_end_week=32,   # August
            stock_peak_weeks=(36, 44),  # September-November
            stock_peak_range=(0.85, 0.95),
            stock_low_weeks=(23, 26),   # June
            stock_low_range=(0.10, 0.15),
            base_production=38_900_000,  # From WASDE
            domestic_consumption=6_400_000,
            export_capacity=31_500_000,
            yearly_consumption=6_400_000
        )

        self.cycles[("UKRAINE", "SOYBEAN")] = CropCycle(
            region="UKRAINE",
            commodity="SOYBEAN",
            plant_start_week=18,  # May
            plant_end_week=22,    # June
            harvest_start_week=36, # September
            harvest_end_week=44,  # November
            stock_peak_weeks=(44, 52),
            stock_peak_range=(0.75, 0.85),
            stock_low_weeks=(32, 35),
            stock_low_range=(0.15, 0.20),
            base_production=13_500_000,
            domestic_consumption=1_500_000,
            export_capacity=12_000_000,
            yearly_consumption=1_500_000
        )

        # ROMANIA
        self.cycles[("ROMANIA", "WHEAT")] = CropCycle(
            region="ROMANIA",
            commodity="WHEAT",
            plant_start_week=36,  # September
            plant_end_week=40,    # October
            harvest_start_week=27,  # July
            harvest_end_week=32,   # August
            stock_peak_weeks=(36, 44),  # September-November
            stock_peak_range=(0.85, 0.90),
            stock_low_weeks=(23, 26),   # June
            stock_low_range=(0.20, 0.25),
            base_production=23_000_000,  # From EU total
            domestic_consumption=3_000_000,
            export_capacity=20_000_000,
            yearly_consumption=3_000_000
        )

        self.cycles[("ROMANIA", "CORN")] = CropCycle(
            region="ROMANIA",
            commodity="CORN",
            plant_start_week=14,  # April
            plant_end_week=18,    # May
            harvest_start_week=36, # September
            harvest_end_week=44,  # November
            stock_peak_weeks=(44, 52),
            stock_peak_range=(0.80, 0.90),
            stock_low_weeks=(32, 35),
            stock_low_range=(0.15, 0.20),
            base_production=32_000_000,
            domestic_consumption=5_000_000,
            export_capacity=26_000_000,
            yearly_consumption=5_000_000
        )

        self.cycles[("ROMANIA", "SOYBEAN")] = CropCycle(
            region="ROMANIA",
            commodity="SOYBEAN",
            plant_start_week=18,  # May
            plant_end_week=22,    # June
            harvest_start_week=36, # September
            harvest_end_week=44,  # November
            stock_peak_weeks=(44, 52),
            stock_peak_range=(0.75, 0.85),
            stock_low_weeks=(32, 35),
            stock_low_range=(0.15, 0.20),
            base_production=20_500_000,
            domestic_consumption=1_500_000,
            export_capacity=17_000_000,
            yearly_consumption=1_500_000
        )

        # FRANCE
        self.cycles[("FRANCE", "WHEAT")] = CropCycle(
            region="FRANCE",
            commodity="WHEAT",
            plant_start_week=36,  # September
            plant_end_week=48,    # December
            harvest_start_week=27,  # July
            harvest_end_week=32,   # August
            stock_peak_weeks=(36, 44),  # September-November
            stock_peak_range=(0.85, 0.90),
            stock_low_weeks=(23, 26),   # June
            stock_low_range=(0.20, 0.25),
            base_production=65_000_000,  # Portion of EU production
            domestic_consumption=16_000_000,
            export_capacity=44_000_000,
            yearly_consumption=16_000_000
        )

        self.cycles[("FRANCE", "CORN")] = CropCycle(
            region="FRANCE",
            commodity="CORN",
            plant_start_week=14,  # April
            plant_end_week=18,    # May
            harvest_start_week=36,  # September
            harvest_end_week=44,   # November
            stock_peak_weeks=(44, 52),  # Nov-Dec
            stock_peak_range=(0.80, 0.90),
            stock_low_weeks=(32, 35),   # August
            stock_low_range=(0.15, 0.20),
            base_production=25_000_000,  # French corn production
            domestic_consumption=8_000_000,
            export_capacity=17_000_000,
            yearly_consumption=8_000_000
        )

        # USA PACIFIC NORTHWEST (PNW)
        self.cycles[("USA_PNW", "WHEAT")] = CropCycle(
            region="USA_PNW",
            commodity="WHEAT",
            plant_start_week=36,  # September
            plant_end_week=40,    # October
            harvest_start_week=27,  # July
            harvest_end_week=32,   # August
            stock_peak_weeks=(36, 44),  # September-November
            stock_peak_range=(0.85, 0.95),
            stock_low_weeks=(23, 26),   # June
            stock_low_range=(0.15, 0.20),
            base_production=38_000_000,  # Portion of US production
            domestic_consumption=3_000_000,
            export_capacity=25_000_000,
            yearly_consumption=3_000_000
        )

        self.cycles[("USA_PNW", "CORN")] = CropCycle(
            region="USA_PNW",
            commodity="CORN",
            plant_start_week=14,  # April
            plant_end_week=18,    # May
            harvest_start_week=36,  # September
            harvest_end_week=44,   # November
            stock_peak_weeks=(44, 52),  # November-December
            stock_peak_range=(0.80, 0.90),
            stock_low_weeks=(32, 35),   # August
            stock_low_range=(0.15, 0.20),
            base_production=40_000_000,  # Portion of US production allocated to PNW
            domestic_consumption=5_000_000,
            export_capacity=35_000_000,
            yearly_consumption=5_000_000
        )

        self.cycles[("USA_PNW", "SOYBEAN")] = CropCycle(
            region="USA_PNW",
            commodity="SOYBEAN",
            plant_start_week=18,  # May
            plant_end_week=22,    # June
            harvest_start_week=36,  # September
            harvest_end_week=44,   # November
            stock_peak_weeks=(44, 52),
            stock_peak_range=(0.75, 0.90),
            stock_low_weeks=(32, 35),
            stock_low_range=(0.15, 0.20),
            base_production=40_000_000,  # Portion of US production
            domestic_consumption=3_000_000,
            export_capacity=37_000_000,
            yearly_consumption=3_000_000
        )

        # Initialize stocks for all cycles
        for region, commodity in self.cycles.keys():
            cycle = self.cycles[(region, commodity)]
            
            # Calculate initial stocks based on typical seasonal patterns
            # We're starting in week 1 (January)
            if cycle.harvest_start_week > 1:
                # If harvest hasn't started yet, stocks should be lower
                initial_stock_pct = random.uniform(0.2, 0.3)
            else:
                # If we're closer to harvest, stocks can be higher
                initial_stock_pct = random.uniform(0.4, 0.5)
                
            cycle.current_stocks = int(cycle.base_production * initial_stock_pct)
            cycle.current_production = cycle.base_production

    def update_cycle(self, region: str, commodity: str, current_week: int, weather_factor: float = 1.0):
        """Update crop cycle status and stock levels"""
        cycle = self.cycles.get((region, commodity))
        if not cycle:
            return None

        # Reset cycle at the start of planting season
        if current_week == cycle.plant_start_week:
            cycle.current_production = int(cycle.base_production * weather_factor)
            cycle.harvest_progress = 0.0

        # Update harvest progress
        if cycle.harvest_start_week <= current_week <= cycle.harvest_end_week:
            weekly_progress = 1.0 / (cycle.harvest_end_week - cycle.harvest_start_week + 1)
            cycle.harvest_progress = min(1.0, cycle.harvest_progress + weekly_progress)
            
            # Add harvested amount to stocks with realistic surge pattern
            # More crop comes in during middle weeks of harvest
            week_in_harvest = current_week - cycle.harvest_start_week
            total_harvest_weeks = cycle.harvest_end_week - cycle.harvest_start_week + 1
            
            # Create a bell curve for harvest intensity
            harvest_intensity = math.exp(
                -0.5 * ((week_in_harvest - total_harvest_weeks/2) / (total_harvest_weeks/4)) ** 2
            )
            new_harvest = int(cycle.current_production * weekly_progress * harvest_intensity)
            cycle.current_stocks += new_harvest

        # Calculate and apply weekly consumption
        # More realistic consumption pattern - varies by season
        season_factor = 1.0 + 0.2 * math.sin(2 * math.pi * current_week / 52)
        base_weekly_consumption = cycle.yearly_consumption / 52
        weekly_consumption = int(base_weekly_consumption * season_factor)
        cycle.current_stocks = max(0, cycle.current_stocks - weekly_consumption)

        # Calculate export drain on stocks
        if cycle.current_stocks > weekly_consumption * 4:  # Only export if sufficient stocks
            weekly_export_capacity = cycle.export_capacity / 52
            potential_exports = min(
                weekly_export_capacity,
                cycle.current_stocks * 0.1  # Max 10% of stocks per week
            )
            cycle.current_stocks = max(0, cycle.current_stocks - int(potential_exports))

        return cycle.current_stocks

    def get_stock_percentage(self, region: str, commodity: str) -> float:
        """Get current stocks as percentage of annual production"""
        cycle = self.cycles.get((region, commodity))
        if cycle and cycle.base_production > 0:
            return cycle.current_stocks / cycle.base_production
        return 0.0

    def get_harvest_progress(self, region: str, commodity: str) -> float:
        """Get current harvest progress (0-1)"""
        cycle = self.cycles.get((region, commodity))
        return cycle.harvest_progress if cycle else 0.0
    
    def get_price_factor(self, region: str, commodity: str, current_week: int) -> float:
        """Calculate price factor based on stock levels and seasonality"""
        cycle = self.cycles.get((region, commodity))
        if not cycle:
            return 1.0

        stock_pct = self.get_stock_percentage(region, commodity)
        
        # Base price factor from stock levels
        if stock_pct < 0.10:
            price_factor = 1.35  # Severe shortage
        elif stock_pct < 0.20:
            price_factor = 1.15  # Moderate shortage
        elif stock_pct > 0.90:
            price_factor = 0.85  # Surplus
        elif stock_pct > 0.80:
            price_factor = 0.95  # Moderate surplus
        else:
            price_factor = 1.0

        # Seasonal adjustments
        # Higher prices during planting and pre-harvest
        if cycle.plant_start_week <= current_week <= cycle.plant_end_week:
            # Planting period premium
            seasonal_factor = 1.05
        elif (cycle.harvest_start_week - 4) <= current_week <= cycle.harvest_start_week:
            # Pre-harvest anxiety premium
            seasonal_factor = 1.08
        elif cycle.harvest_start_week <= current_week <= cycle.harvest_end_week:
            # Harvest pressure discount
            seasonal_factor = 0.95
        else:
            seasonal_factor = 1.0

        # Consider export activity
        export_intensity = min(1.0, (cycle.export_capacity / 52) / cycle.current_stocks if cycle.current_stocks > 0 else 0)
        export_factor = 1.0 + (export_intensity * 0.05)  # Up to 5% premium for heavy export periods

        return price_factor * seasonal_factor * export_factor

    def get_export_availability(self, region: str, commodity: str) -> float:
        """Calculate percentage of normal export capacity currently available"""
        cycle = self.cycles.get((region, commodity))
        if not cycle or cycle.current_stocks <= 0:
            return 0.0

        # Calculate weeks of coverage at current stock levels
        weekly_consumption = cycle.yearly_consumption / 52
        weeks_coverage = cycle.current_stocks / weekly_consumption

        if weeks_coverage < 4:  # Less than 4 weeks coverage
            return 0.0  # No exports
        elif weeks_coverage < 8:  # 4-8 weeks coverage
            return 0.5  # 50% of normal export capacity
        else:
            return 1.0  # Full export capacity

    def get_cycle_status(self, region: str, commodity: str, current_week: int) -> Dict:
        """Get comprehensive status of a crop cycle"""
        cycle = self.cycles.get((region, commodity))
        if not cycle:
            return None

        # Determine current phase
        in_planting = cycle.plant_start_week <= current_week <= cycle.plant_end_week
        in_harvest = cycle.harvest_start_week <= current_week <= cycle.harvest_end_week
        
        # Calculate days to next phase
        weeks_to_harvest = (cycle.harvest_start_week - current_week) % 52 if not in_harvest else 0
        weeks_to_planting = (cycle.plant_start_week - current_week) % 52 if not in_planting else 0

        return {
            "current_stocks": cycle.current_stocks,
            "stock_percentage": self.get_stock_percentage(region, commodity),
            "harvest_progress": cycle.harvest_progress if in_harvest else 0.0,
            "planting_progress": ((current_week - cycle.plant_start_week) / 
                                (cycle.plant_end_week - cycle.plant_start_week)) if in_planting else 0.0,
            "in_planting": in_planting,
            "in_harvest": in_harvest,
            "weeks_to_harvest": weeks_to_harvest,
            "weeks_to_planting": weeks_to_planting,
            "export_availability": self.get_export_availability(region, commodity),
            "current_production": cycle.current_production,
            "projected_ending_stocks": self._project_ending_stocks(region, commodity, current_week)
        }

    def _project_ending_stocks(self, region: str, commodity: str, current_week: int) -> int:
        """Project ending stocks based on current trajectory"""
        cycle = self.cycles.get((region, commodity))
        if not cycle:
            return 0

        # Calculate remaining consumption
        weeks_remaining = 52 - current_week
        weekly_consumption = cycle.yearly_consumption / 52
        remaining_consumption = weekly_consumption * weeks_remaining

        # Calculate remaining harvest
        if cycle.harvest_start_week <= current_week <= cycle.harvest_end_week:
            remaining_harvest = cycle.current_production * (1 - cycle.harvest_progress)
        elif current_week < cycle.harvest_start_week:
            remaining_harvest = cycle.current_production
        else:
            remaining_harvest = 0

        # Project ending stocks
        projected_stocks = (cycle.current_stocks + remaining_harvest - 
                        remaining_consumption - (cycle.export_capacity / 52 * weeks_remaining))
        
        return max(0, int(projected_stocks))

    def get_market_signals(self, region: str, commodity: str, current_week: int) -> Dict:
        """Get market signals for trading decisions"""
        cycle = self.cycles.get((region, commodity))
        if not cycle:
            return None

        status = self.get_cycle_status(region, commodity, current_week)
        stock_pct = status["stock_percentage"]

        # Calculate stock level signal
        if stock_pct < 0.15:
            stock_signal = "CRITICALLY_LOW"
        elif stock_pct < 0.25:
            stock_signal = "LOW"
        elif stock_pct > 0.85:
            stock_signal = "SURPLUS"
        elif stock_pct > 0.75:
            stock_signal = "HIGH"
        else:
            stock_signal = "NORMAL"

        # Calculate seasonal signal
        if cycle.plant_start_week <= current_week <= cycle.plant_end_week:
            seasonal_signal = "PLANTING"
        elif cycle.harvest_start_week <= current_week <= cycle.harvest_end_week:
            seasonal_signal = "HARVEST"
        elif (cycle.harvest_start_week - 4) <= current_week < cycle.harvest_start_week:
            seasonal_signal = "PRE_HARVEST"
        else:
            seasonal_signal = "INTER_SEASON"

        return {
            "stock_signal": stock_signal,
            "seasonal_signal": seasonal_signal,
            "export_signal": "AVAILABLE" if status["export_availability"] > 0.8 else 
                            "LIMITED" if status["export_availability"] > 0.3 else "RESTRICTED",
            "price_factor": self.get_price_factor(region, commodity, current_week),
            "projected_ending_stocks": status["projected_ending_stocks"],
            "current_stocks": status["current_stocks"],
            "stock_trend": "DECLINING" if cycle.current_stocks < cycle.yearly_consumption / 12 else
                        "STABLE" if cycle.current_stocks < cycle.yearly_consumption / 6 else "BUILDING"
        }

class TenderStatus(Enum):
    OPEN = "OPEN"
    PENDING_AWARD = "PENDING_AWARD"
    AWARDED = "AWARDED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"

class OfferStatus(Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    PARTIALLY_ACCEPTED = "PARTIALLY_ACCEPTED"
    REJECTED = "REJECTED"

@dataclass
class TenderAnnouncement:
    """Represents a tender announcement from a buyer"""
    buyer: str
    commodity: str
    total_quantity: int
    min_cargo_size: int
    max_cargo_size: int
    permitted_origins: List[str]
    shipment_start: int
    shipment_end: int
    payment_terms: int
    max_vessels: int
    special_conditions: List[str]
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: TenderStatus = TenderStatus.OPEN
    submission_deadline: int = None
    announcement_date: int = None
    required_vessel_type: str = None  # New field for specific vessel requirement
    blacklisted_participants: List[str] = field(default_factory=list)  # New field for blacklisted participants
    participation_cost: int = 10000  # New field for participation cost
    blacklisted_until: Optional[int] = None  # Week number when blacklist expires
    delivered_quantity: int = 0  # Track how much has been delivered
    
@dataclass
class TenderDelivery:
    tender_id: str
    offer_id: str
    quantity: int
    delivered: bool = False
    delivery_week: Optional[int] = None
    delivery_year: Optional[int] = None


@dataclass
class TenderOffer:
    """Represents an offer made by a participant"""
    tender_id: str
    participant: str
    origin: str
    quantity: int                  # Total MT offered
    num_vessels: int              # Number of vessels
    price: float                  # USD/MT CFR
    submission_week: int
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: OfferStatus = OfferStatus.PENDING
    awarded_quantity: int = 0     # Quantity actually awarded

class CompetitorBehavior:
    """Defines competitor behavior and offer generation"""
    def __init__(self, game):  # Now takes game instance
        self.game = game
        self.competitors = {
            "VITERRA": {
                "aggression": 0.85,         # Likelihood to bid aggressively
                "margin_target": 0.035,     # Target profit margin
                "participation_rate": 0.9,  # Likelihood to participate
                "multi_vessel": 0.7        # Likelihood to offer multiple vessels
            },
            "CARGILL": {
                "aggression": 0.7,
                "margin_target": 0.035,
                "participation_rate": 0.9,
                "multi_vessel": 0.8
            },
            "COFCO": {
                "aggression": 0.9,
                "margin_target": 0.04,
                "participation_rate": 0.7,
                "multi_vessel": 0.6
            },
            "ADM": {
                "aggression": 0.75,
                "margin_target": 0.05,
                "participation_rate": 0.85,
                "multi_vessel": 0.75
            },
            "LDC": {
                "aggression": 0.85,
                "margin_target": 0.045,
                "participation_rate": 0.88,
                "multi_vessel": 0.85
            },
            "OLAM": {
                "aggression": 0.95,
                "margin_target": 0.055,
                "participation_rate": 0.85,
                "multi_vessel": 0.65
            }
        }

    def generate_competitor_offers(self, tender: TenderAnnouncement) -> List[TenderOffer]:
        """Generate competitor offers for a tender"""
        offers = []
        
        for company, behavior in self.competitors.items():
            # Early exit if company doesn't want to participate
            if random.random() > behavior["participation_rate"]:
                continue
                
            # Select origins to offer from
            num_origins = random.randint(1, len(tender.permitted_origins))
            selected_origins = random.sample(tender.permitted_origins, num_origins)
            
            for origin in selected_origins:
                # Get FOB price
                fob_quote = self.game.market.fob_markets.get((tender.commodity, origin))
                # Add check for valid quote
                if not fob_quote or not fob_quote.has_valid_quote():
                    continue
                
                # Get freight rate for required vessel type
                freight_quotes = self.game.market.freight_markets.get((origin, tender.buyer))
                if not freight_quotes or tender.required_vessel_type not in freight_quotes:
                    continue
                
                # Use the specific vessel type required by tender
                freight_quote = freight_quotes[tender.required_vessel_type]
                vessel_capacity = VesselType.__dict__[tender.required_vessel_type]["capacity"]
                
                # Ensure we have valid offer price and freight rate
                if fob_quote.offer is None or freight_quote.rate is None:
                    continue
                
                # Calculate base cost
                base_cost = fob_quote.offer + freight_quote.rate
                
                # Calculate working capital required
                payment_delay = self.game.market.destinations[tender.buyer].payment_delay_days
                # Add 1% per month financing cost
                financing_cost = (payment_delay / 30) * 0.01 * base_cost
                
                # Add risk premium based on destination
                dest_risk = self.game.market.destinations[tender.buyer].risk_level
                risk_premium = (dest_risk - 1) * 0.005 * base_cost  # 0.5% per risk level above 1
                
                # Calculate margin considering costs and risk
                target_margin = behavior["margin_target"]
                
                # Market condition adjustment
                market_condition = self.game.market.local_market_conditions[tender.buyer]
                if market_condition > 1.05:  # Strong demand
                    target_margin *= 1.2
                elif market_condition < 0.95:  # Weak demand
                    target_margin *= 0.8
                
                # Competitive adjustment based on aggression
                if random.random() < behavior["aggression"]:
                    target_margin *= random.uniform(0.7, 0.9)  # More aggressive
                else:
                    target_margin *= random.uniform(1.0, 1.2)  # More conservative
                
                # Calculate final price including all costs and margin
                offer_price = base_cost + financing_cost + risk_premium
                offer_price *= (1 + target_margin)
                offer_price = round(offer_price, 2)

                
                # Calculate number of vessels within tender constraints
                max_possible_vessels = min(
                    tender.max_vessels,
                    tender.total_quantity // vessel_capacity
                )
                
                if max_possible_vessels < 1:
                    continue
                
                # Determine number of vessels to offer
                if random.random() < behavior["multi_vessel"]:
                    num_vessels = random.randint(1, max_possible_vessels)
                else:
                    num_vessels = 1
                
                quantity = num_vessels * vessel_capacity
                if quantity > tender.total_quantity:
                    continue
                
                offers.append(TenderOffer(
                    tender_id=tender.id,
                    participant=company,
                    origin=origin,
                    quantity=quantity,
                    num_vessels=num_vessels,
                    price=offer_price,
                    submission_week=self.game.market.current_week
                ))
        
        return offers

class TenderManager:
    def __init__(self, game):
        self.game = game
        self.market = game.market
        self.active_tenders: Dict[str, TenderAnnouncement] = {}
        self.historical_tenders: Dict[str, TenderAnnouncement] = {}
        self.offers: Dict[str, List[TenderOffer]] = {}
        self.competitor_behavior = CompetitorBehavior(game) 
        # Player's awarded tenders tracking
        self.player_awarded_tenders: List[Tuple[TenderAnnouncement, TenderOffer]] = []
        self.last_generation_week = 0
        
        # Initialize tender results queue
        self.tender_results_queue = []  # Add this line to initialize the queue
        
        self.buyer_preferences = {
            "CASABLANCA": {
                "preferred_commodities": ["WHEAT", "CORN"],
                "typical_quantity": (150000, 300000),
                "preferred_origins": ["ROUEN", "SANTOS", "ODESSA", "NOVOROSSIYSK", "CONSTANTA", "BURGAS", "ROSARIO"]
            },
            "BANDAR_IMAM": {
                "preferred_commodities": ["CORN", "SOYBEAN", "WHEAT"],
                "typical_quantity": (185000, 280000),
                "preferred_origins": ["SANTOS", "ROSARIO", "ODESSA", "NOVOROSSIYSK", "CONSTANTA"]
            },
            "ALEXANDRIA": {
                "preferred_commodities": ["WHEAT", "CORN"],
                "typical_quantity": (350000, 800000),
                "preferred_origins": ["ODESSA", "NOVOROSSIYSK", "CONSTANTA", "BURGAS", "ROUEN"]
            },
            "ALGIERS": {
                "preferred_commodities": ["WHEAT", "CORN"],
                "typical_quantity": (250000, 500000),
                "preferred_origins": ["ROUEN", "NOVOROSSIYSK", "CONSTANTA", "BURGAS", "ODESSA"]
            },
            "CHITTAGONG": {
                "preferred_commodities": ["WHEAT", "CORN"],
                "typical_quantity": (185000, 300000),
                "preferred_origins": ["PARANAGUA", "SANTOS", "ODESSA", "NOVOROSSIYSK"]
            },
            "VIETNAM": {
                "preferred_commodities": ["WHEAT", "CORN"],
                "typical_quantity": (185000, 300000),
                "preferred_origins": ["PARANAGUA", "SANTOS", "ODESSA", "NOVOROSSIYSK", "PNW", "ROSARIO"]
            },
            "JAKARTA": {
                "preferred_commodities": ["WHEAT", "CORN"],
                "typical_quantity": (185000, 300000),
                "preferred_origins": ["PARANAGUA", "SANTOS", "ODESSA", "NOVOROSSIYSK", "PNW", "ROSARIO"]
            },
        }

        self.weekly_tender_tracker = {
            buyer: set() for buyer in self.buyer_preferences.keys()
        }
        # Add a week tracker to know when to reset
        self.last_tender_week = 0
    
    def blacklist_participant(self, participant: str, buyer: str, until_week: int):
        """Blacklist a participant from a specific buyer's tenders"""
        # Add buyer-specific blacklist tracking if not exists
        if not hasattr(self, 'buyer_blacklists'):
            self.buyer_blacklists = {}
        
        if buyer not in self.buyer_blacklists:
            self.buyer_blacklists[buyer] = {}
        
        self.buyer_blacklists[buyer][participant] = until_week

    def is_participant_blacklisted(self, participant: str, buyer: str, current_week: int) -> bool:
        """Check if participant is blacklisted from a specific buyer"""
        if not hasattr(self, 'buyer_blacklists'):
            return False
            
        if buyer not in self.buyer_blacklists:
            return False
            
        blacklist_until = self.buyer_blacklists[buyer].get(participant)
        if not blacklist_until:
            return False
            
        return current_week < blacklist_until
        
    def generate_tenders(self, current_week: int):
        """Generate new tenders based on market conditions"""
        current_year = self.game.market.year
        
       
        # Reset tracking at the start of each year
        if current_week == 1:
            self.last_generation_week = 0  # Reset for new year
            self.weekly_tender_tracker = {
                buyer: set() for buyer in self.buyer_preferences.keys()
            }
        
        if current_week % 6 != 0 or current_week == self.last_generation_week:
            return
        
        self.last_generation_week = current_week
        
        # Generate 1-3 new tenders
        num_tenders = random.randint(1, 3)
        
        generated_count = 0
        for _ in range(num_tenders):
            # Get list of buyers who haven't used all their commodities
            available_buyers = [
                buyer for buyer, tendered_commodities in self.weekly_tender_tracker.items()
                if len(tendered_commodities) < len(self.buyer_preferences[buyer]["preferred_commodities"])
            ]
            
            if not available_buyers:
                continue
                
            # Select buyer and their preferences
            buyer = random.choice(available_buyers)
            prefs = self.buyer_preferences[buyer]
            
            # Get commodities this buyer hasn't tendered for yet
            available_commodities = [
                commodity for commodity in prefs["preferred_commodities"]
                if commodity not in self.weekly_tender_tracker[buyer]
            ]
            
            if not available_commodities:
                continue
                
            # Select commodity from available ones
            commodity = random.choice(available_commodities)
            
            # Mark this commodity as tendered for this buyer
            self.weekly_tender_tracker[buyer].add(commodity)
            
            # Select a specific vessel type requirement
            required_vessel_type = random.choice(["HANDYMAX", "SUPRAMAX", "PANAMAX"])
            vessel_capacity = VesselType.__dict__[required_vessel_type]["capacity"]
            
            # Calculate tender quantity based on vessel size
            num_vessels = random.randint(1, 3)
            total_quantity = num_vessels * vessel_capacity
            
            # Set shipment window
            window_length = random.choice([8, 12, 16, 24])  # Weeks
            start_week = current_week + random.randint(6, 12)
            
            # Handle year rollover for shipment window
            end_week = start_week + window_length
            shipment_year = current_year
            
            # Adjust for year boundary
            if start_week > 52:
                start_week = start_week - 52
                shipment_year += 1
            
            if end_week > 52:
                end_week = end_week - 52
            
            # Create tender
            tender = TenderAnnouncement(
                buyer=buyer,
                commodity=commodity,
                total_quantity=total_quantity,
                min_cargo_size=vessel_capacity,
                max_cargo_size=vessel_capacity,
                permitted_origins=prefs["preferred_origins"],
                shipment_start=start_week,
                shipment_end=end_week,
                payment_terms=random.choice([30, 45, 60, 90]),
                max_vessels=num_vessels,
                special_conditions=[required_vessel_type],
                required_vessel_type=required_vessel_type,
                announcement_date=current_week,
                submission_deadline=current_week + 2,
                participation_cost=10000
            )
            
            self.active_tenders[tender.id] = tender
            generated_count += 1

    def submit_offer(self, tender_id: str, offer: TenderOffer) -> bool:
        """Submit a new offer for a tender"""
        if tender_id not in self.active_tenders:
            return False
            
        tender = self.active_tenders[tender_id]
        if tender.status != TenderStatus.OPEN:
            return False
            
        if offer.quantity > tender.total_quantity:
            return False
            
        if tender_id not in self.offers:
            self.offers[tender_id] = []
            
        self.offers[tender_id].append(offer)
        return True

    def evaluate_offers(self, tender_id: str) -> Dict[str, List[TenderOffer]]:
        """
        Evaluate all offers for a tender and determine awards based on price competitiveness
        and vessel capacity constraints.

        The evaluation process:
        1. Validates tender and offer existence
        2. Sorts offers by price (lowest first)
        3. Awards quantities starting with lowest price offers
        4. Respects vessel size requirements and remaining quantity
        5. Sets appropriate status for each offer
        6. Updates tender status based on award results

        Args:
            tender_id (str): The unique identifier of the tender to evaluate

        Returns:
            Dict[str, List[TenderOffer]]: Dictionary mapping participant names to their awarded offers.
            Empty dict if no awards made or invalid tender.
        """
        # Basic validation - check tender and offers exist
        if tender_id not in self.active_tenders or tender_id not in self.offers:
            return {}
            
        tender = self.active_tenders[tender_id]
        all_offers = self.offers[tender_id]
        
        if not all_offers:
            return {}
        
        # Sort offers by price (lowest first) to ensure best prices get priority
        sorted_offers = sorted(all_offers, key=lambda x: x.price)
        remaining_quantity = tender.total_quantity
        awards = []
        
        # Get the required vessel capacity from tender specifications
        vessel_capacity = VesselType.__dict__[tender.required_vessel_type]["capacity"]
        
        # Process each offer in price order
        for offer in sorted_offers:
            # Skip if remaining quantity is less than one vessel
            if remaining_quantity < vessel_capacity:
                offer.status = OfferStatus.REJECTED
                continue
                
            # Calculate how many vessels can be awarded based on remaining quantity
            possible_vessels = min(
                offer.num_vessels,  # Don't exceed offered vessels
                remaining_quantity // vessel_capacity  # Don't exceed tender quantity
            )
            
            if possible_vessels > 0:
                # Calculate award quantity based on vessel capacity
                award_quantity = possible_vessels * vessel_capacity
                lowest_price = sorted_offers[0].price
                
                # Accept offers within 5% of lowest price to allow some price flexibility
                if offer.price <= lowest_price * 1.05:
                    # Set appropriate offer status based on awarded quantity
                    if award_quantity == offer.quantity:
                        offer.status = OfferStatus.ACCEPTED
                    else:
                        offer.status = OfferStatus.PARTIALLY_ACCEPTED
                    
                    # Record awarded quantity and add to awards list
                    offer.awarded_quantity = award_quantity
                    awards.append(offer)
                    remaining_quantity -= award_quantity
                else:
                    offer.status = OfferStatus.REJECTED
            else:
                offer.status = OfferStatus.REJECTED
        
        # Update tender status based on award results
        if awards:
            tender.status = TenderStatus.AWARDED
            # Group awards by participant for easier processing
            awards_by_participant = {}
            for offer in awards:
                if offer.participant not in awards_by_participant:
                    awards_by_participant[offer.participant] = []
                awards_by_participant[offer.participant].append(offer)
            return awards_by_participant
        else:
            # If no awards were made, mark tender as cancelled
            tender.status = TenderStatus.CANCELLED
            return {}
    

    def process_tender_results(self, tender: TenderAnnouncement) -> Tuple[str, List[TenderOffer]]:
        """Process a single tender's results and return structured data"""
        # Generate competitor offers
        competitor_offers = self.competitor_behavior.generate_competitor_offers(tender) 
        for offer in competitor_offers:
            self.submit_offer(tender.id, offer)
            
        # Evaluate all offers
        awards = self.evaluate_offers(tender.id)
        
        # Flatten awards into a single list while preserving tender ID
        if awards:
            all_awards = []
            for participant_awards in awards.values():
                all_awards.extend(participant_awards)
            return (tender.id, all_awards)
        return (tender.id, [])

    def update_tenders(self, current_week: int):
        """Update tender statuses based on current week"""
        self.generate_tenders(current_week)
        results = []
        
        # Process existing tenders
        for tender_id, tender in list(self.active_tenders.items()):
            if current_week > tender.submission_deadline and tender.status == TenderStatus.OPEN:
                # Process this tender
                tender_id, awards = self.process_tender_results(tender)
                
                # Move to historical before adding results
                self.historical_tenders[tender_id] = tender
                del self.active_tenders[tender_id]
                
                # Only add to results if there are awards
                if awards:
                    results.append((tender_id, awards))
                    
        return results

    def get_tender_details(self, tender_id: str) -> Dict:
        """Get detailed information about a tender"""
        tender = self.active_tenders.get(tender_id) or self.historical_tenders.get(tender_id)
        if not tender:
            return None
            
        offers = self.offers.get(tender_id, [])
        
        return {
            "tender": tender,
            "offers": offers,
            "total_offers": len(offers),
            "lowest_offer": min((o.price for o in offers), default=None),
            "highest_offer": max((o.price for o in offers), default=None),
            "average_offer": sum((o.price for o in offers), default=0) / len(offers) if offers else None
        }

    # Add this method to the TenderManager class
    def analyze_tender_pricing(self, tender: TenderAnnouncement, offer: TenderOffer) -> dict:
        """Analyze the pricing components of a tender offer"""
        origin = offer.origin
        
        # Get market quotes
        fob_quote = self.game.market.fob_markets.get((tender.commodity, origin))
        if not fob_quote or not fob_quote.has_valid_quote():  # Added valid quote check
            return None
            
        freight_quotes = self.game.market.freight_markets.get((origin, tender.buyer))
        if not freight_quotes or tender.required_vessel_type not in freight_quotes:
            return None
            
        freight_quote = freight_quotes[tender.required_vessel_type]
        
        # Calculate components
        base_fob = fob_quote.offer
        freight = freight_quote.rate
        landed_cost = base_fob + freight
        
        # Calculate financing cost
        payment_delay = self.game.market.destinations[tender.buyer].payment_delay_days
        financing_cost = (payment_delay / 30) * 0.01 * landed_cost
        
        # Calculate risk premium
        dest_risk = self.game.market.destinations[tender.buyer].risk_level
        risk_premium = (dest_risk - 1) * 0.005 * landed_cost
        
        # Calculate implied margin
        total_cost = landed_cost + financing_cost + risk_premium
        implied_margin = ((offer.price / total_cost) - 1) * 100
        
        return {
            "fob_cost": base_fob,
            "freight_cost": freight,
            "landed_cost": landed_cost,
            "financing_cost": financing_cost,
            "risk_premium": risk_premium,
            "total_cost": total_cost,
            "offer_price": offer.price,
            "implied_margin": implied_margin
        }

class TradeStatus(Enum):
    SAILING = "SAILING"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"

@dataclass
class MarketQuote:
    bid: float
    offer: float
    bid_size: int
    offer_size: int
    last_price: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    inventory: int = field(default_factory=lambda: random.randint(100000, 500000))
    six_month_high: float = field(default_factory=lambda: float('-inf'))
    six_month_low: float = field(default_factory=lambda: float('inf'))
    price_history: List[Tuple[int, float, float]] = field(default_factory=list)  # [(week, bid, offer), ...]
    new_high_this_week: bool = False  # Track if new high set this week
    new_low_this_week: bool = False   # Track if new low set this week

    def update_historical_prices(self, current_week: int):
        """Update 6-month high/low prices and maintain price history"""
        # Only update if we have valid prices
        if self.bid is not None and self.offer is not None:
            # Check for new high/low
            self.new_high_this_week = self.bid > self.six_month_high
            self.new_low_this_week = self.bid < self.six_month_low
            
            if self.new_high_this_week:
                self.six_month_high = self.bid
            if self.new_low_this_week:
                self.six_month_low = self.bid
            
            # Add to price history - ensure both bid and offer are included
            self.price_history.append((current_week, self.bid, self.offer))
            
            # Keep only last 24 weeks (6 months) of history
            while len(self.price_history) > 24:
                self.price_history.pop(0)
        
        # Clear invalid history entries
        self.price_history = [(week, bid, offer) for week, bid, offer in self.price_history 
                            if bid is not None and offer is not None]

        # Debug message to help track history building
        if len(self.price_history) > 0:
            print(f"Price history length: {len(self.price_history)}")

    def has_valid_quote(self) -> bool:
        """Check if quote has valid prices"""
        return self.bid is not None and self.offer is not None

    def price_direction(self) -> int:
        """Returns color code for price direction"""
        if not self.has_valid_quote() or not self.last_price:
            return 7  # Neutral color when no valid prices
        if abs(self.bid - self.last_price) < 0.01:
            return 7
        return 4 if self.bid > self.last_price else 3

    def has_sufficient_history(self) -> bool:
        """Check if there's enough valid price history to display graph"""
        valid_points = [(week, bid, offer) for week, bid, offer in self.price_history 
                       if bid is not None and offer is not None]
        return len(valid_points) >= 2  # Need at least 2 valid points
        
    def has_valid_inventory(self) -> bool:
        """Check if there is sufficient inventory for quotes"""
        return self.inventory > 0

    def get_available_quantity(self, requested_quantity: int) -> int:
        """Get available quantity up to requested amount"""
        return min(requested_quantity, self.inventory) if self.has_valid_inventory() else 0
        
    def get_displayable_quote(self) -> Tuple[Optional[float], Optional[float]]:
        """Return (bid, offer) if valid quote exists, else (None, None)"""
        if self.has_valid_quote():
            return (self.bid, self.offer)
        return (None, None)

@dataclass
class FreightQuote:
    rate: float  # USD/MT
    duration_days: int  # Sailing time
    vessel_size: str  # Panamax/Supramax etc
    last_rate: float = 0.0
    capacity: int = 60000  # Default capacity in MT

@dataclass
class Trade:
    commodity: str
    origin: str
    destination: str
    quantity: int
    fob_price: float
    freight_rate: float
    vessel_type: str
    execution_week: int
    execution_year: int
    status: TradeStatus
    arrival_week: Optional[int] = None
    arrival_year: Optional[int] = None
    fob_cost: float = 0.0
    freight_cost: float = 0.0
    total_cost: float = 0.0
    revenue: float = 0.0
    estimated_profit: float = 0.0

class Port:
    def __init__(self, name: str, region: str, risk_level: int, payment_delay_days: int):
        self.name = name
        self.region = region
        self.risk_level = risk_level  # 1-5 (1=lowest risk)
        self.payment_delay_days = payment_delay_days
        self.congestion_level = 0  # 0-100
        self.weather_delay = 0  # additional days
        self.status_history: List[str] = []
        self.storage_capacity = 1000000  # MT
        self.current_storage = 0  # MT
        self.is_deep_sea = True  # Determines vessel size restrictions

    def get_total_delay(self) -> int:
        congestion_days = int(self.congestion_level / 20)  # every 20 points = 1 day
        return congestion_days + self.weather_delay
    
    def add_status(self, status: str):
        timestamp = datetime.now().strftime("%H:%M")
        self.status_history.append(f"[{timestamp}] {status}")
        if len(self.status_history) > 10:
            self.status_history.pop(0)

class VesselType:
    """Constants for vessel specifications with realistic economies of scale"""
    HANDYMAX = {
        "capacity": 28000,          # Smaller capacity
        "daily_rate_atl": 14000,    # Higher daily rate per MT of capacity
        "daily_rate_pac": 13800,
        "consumption": 28,          # MT fuel per day
        "speed": 12.5,             # Slightly slower
        "load_rate": 8000,         # Slower loading/discharge
        "discharge_rate": 8000,
        "overhead_factor": 1.15     # Higher overhead per MT
    }
    
    SUPRAMAX = {
        "capacity": 55000,
        "daily_rate_atl": 16500,    # Moderate daily rate per MT of capacity
        "daily_rate_pac": 16200,
        "consumption": 32,          # Better fuel efficiency per MT
        "speed": 13.0,
        "load_rate": 12000,
        "discharge_rate": 12000,
        "overhead_factor": 1.12     # Moderate overhead per MT
    }
    
    PANAMAX = {
        "capacity": 82000,          # Larger capacity
        "daily_rate_atl": 18500,    # Lower daily rate per MT of capacity
        "daily_rate_pac": 18200,
        "consumption": 36,          # Best fuel efficiency per MT
        "speed": 13.5,
        "load_rate": 15000,        # Faster loading/discharge
        "discharge_rate": 15000,
        "overhead_factor": 1.10     # Lower overhead per MT
    }

@dataclass
class StorageFacility:
    """Represents a grain storage facility at a port"""
    name: str
    total_capacity: int        # MT
    available_capacity: int    # MT
    monthly_cost: float       # USD/MT/month
    handling_cost: float      # USD/MT for in/out
    min_throughput: int       # Minimum MT per month
    max_intake_rate: int      # MT per day
    max_outtake_rate: int     # MT per day
    current_inventory: Dict[str, int] = field(default_factory=dict)  # By commodity
    
    def can_accept(self, quantity: int) -> bool:
        """Check if facility can accept quantity"""
        return self.available_capacity >= quantity
    
    def store_grain(self, commodity: str, quantity: int) -> bool:
        """Attempt to store grain in facility"""
        if not self.can_accept(quantity):
            return False
            
        if commodity not in self.current_inventory:
            self.current_inventory[commodity] = 0
            
        self.current_inventory[commodity] += quantity
        self.available_capacity -= quantity
        return True
    
    def remove_grain(self, commodity: str, quantity: int) -> bool:
        """Attempt to remove grain from facility"""
        if commodity not in self.current_inventory or \
           self.current_inventory[commodity] < quantity:
            return False
            
        self.current_inventory[commodity] -= quantity
        self.available_capacity += quantity
        return True
    
    def calculate_storage_cost(self, quantity: int, days: int) -> float:
        """Calculate storage cost for a period"""
        months = days / 30
        return quantity * self.monthly_cost * months

@dataclass
class StorageTransaction:
    """Represents a storage position"""
    facility: str
    commodity: str
    quantity: int
    entry_date: int  # Game week
    entry_price: float
    storage_cost_paid: float = 0.0
    handling_cost_paid: float = 0.0
    last_storage_payment_week: int = field(default_factory=lambda: 0)  # Track last payment week

class FreightCalculator:
    """Calculate freight rates based on time charter economics"""
    
    def __init__(self):
        # Distance matrix structure (values in nautical miles)
        self.distances = {
            # From Santos (base Brazilian port)
            ("SANTOS", "NINGBO"): 13211,
            ("SANTOS", "ALGIERS"): 4789,
            ("SANTOS", "ALEXANDRIA"): 5642,
            ("SANTOS", "BANDAR_IMAM"): 8548,
            ("SANTOS", "VIETNAM"): 12450,
            ("SANTOS", "CASABLANCA"): 4410,
            ("SANTOS", "TUNIS"): 5115,
            ("SANTOS", "MERSIN"): 6280,
            ("SANTOS", "KARACHI"): 8120,
            ("SANTOS", "JAKARTA"): 11890,
            ("SANTOS", "CHITTAGONG"): 10740,

            # From Paranagua (Santos + ~122nm for southern position)
            ("PARANAGUA", "NINGBO"): 13333,
            ("PARANAGUA", "ALGIERS"): 4911,
            ("PARANAGUA", "ALEXANDRIA"): 5764,
            ("PARANAGUA", "BANDAR_IMAM"): 8670,
            ("PARANAGUA", "VIETNAM"): 12572,
            ("PARANAGUA", "CASABLANCA"): 4532,
            ("PARANAGUA", "TUNIS"): 5237,
            ("PARANAGUA", "MERSIN"): 6402,
            ("PARANAGUA", "KARACHI"): 8242,
            ("PARANAGUA", "JAKARTA"): 12012,
            ("PARANAGUA", "CHITTAGONG"): 10862,

            # From Rosario (Santos + ~1095nm for River Plate position)
            ("ROSARIO", "NINGBO"): 14306,
            ("ROSARIO", "ALGIERS"): 5884,
            ("ROSARIO", "ALEXANDRIA"): 6737,
            ("ROSARIO", "BANDAR_IMAM"): 9033,
            ("ROSARIO", "VIETNAM"): 13545,
            ("ROSARIO", "CASABLANCA"): 5505,
            ("ROSARIO", "TUNIS"): 6210,
            ("ROSARIO", "MERSIN"): 7375,
            ("ROSARIO", "KARACHI"): 9215,
            ("ROSARIO", "JAKARTA"): 12985,
            ("ROSARIO", "CHITTAGONG"): 11835,

            # From PNW (Seattle/Tacoma)
            ("PNW", "NINGBO"): 5100,
            ("PNW", "VIETNAM"): 6340,
            ("PNW", "ALGIERS"): 8450,
            ("PNW", "ALEXANDRIA"): 8920,
            ("PNW", "BANDAR_IMAM"): 9780,
            ("PNW", "CASABLANCA"): 8071,
            ("PNW", "TUNIS"): 8776,
            ("PNW", "MERSIN"): 9558,
            ("PNW", "KARACHI"): 9352,
            ("PNW", "JAKARTA"): 7560,
            ("PNW", "CHITTAGONG"): 8980,

            # From Odessa (+216nm from Burgas base)
            ("ODESSA", "NINGBO"): 10816,
            ("ODESSA", "VIETNAM"): 9955,
            ("ODESSA", "ALEXANDRIA"): 1064,
            ("ODESSA", "ALGIERS"): 1684,
            ("ODESSA", "BANDAR_IMAM"): 4456,
            ("ODESSA", "CASABLANCA"): 2105,
            ("ODESSA", "TUNIS"): 1331,
            ("ODESSA", "MERSIN"): 924,
            ("ODESSA", "KARACHI"): 4028,
            ("ODESSA", "JAKARTA"): 9235,
            ("ODESSA", "CHITTAGONG"): 6980,

            # From Novorossiysk (+330nm from Burgas base)
            ("NOVOROSSIYSK", "NINGBO"): 10930,
            ("NOVOROSSIYSK", "VIETNAM"): 10069,
            ("NOVOROSSIYSK", "ALEXANDRIA"): 1178,
            ("NOVOROSSIYSK", "ALGIERS"): 1798,
            ("NOVOROSSIYSK", "BANDAR_IMAM"): 4570,
            ("NOVOROSSIYSK", "CASABLANCA"): 2219,
            ("NOVOROSSIYSK", "TUNIS"): 1445,
            ("NOVOROSSIYSK", "MERSIN"): 1038,
            ("NOVOROSSIYSK", "KARACHI"): 4142,
            ("NOVOROSSIYSK", "JAKARTA"): 9349,
            ("NOVOROSSIYSK", "CHITTAGONG"): 7094,

            # From Constanta (+70nm from Burgas base)
            ("CONSTANTA", "NINGBO"): 10670,
            ("CONSTANTA", "VIETNAM"): 9809,
            ("CONSTANTA", "ALEXANDRIA"): 918,
            ("CONSTANTA", "ALGIERS"): 1538,
            ("CONSTANTA", "BANDAR_IMAM"): 4310,
            ("CONSTANTA", "CASABLANCA"): 1959,
            ("CONSTANTA", "TUNIS"): 1185,
            ("CONSTANTA", "MERSIN"): 778,
            ("CONSTANTA", "KARACHI"): 3882,
            ("CONSTANTA", "JAKARTA"): 9089,
            ("CONSTANTA", "CHITTAGONG"): 6834,

            # From Rouen
            ("ROUEN", "NINGBO"): 10400,
            ("ROUEN", "VIETNAM"): 9539,
            ("ROUEN", "ALEXANDRIA"): 3148,
            ("ROUEN", "ALGIERS"): 1468,
            ("ROUEN", "BANDAR_IMAM"): 6467,
            ("ROUEN", "CASABLANCA"): 889,
            ("ROUEN", "TUNIS"): 1915,
            ("ROUEN", "MERSIN"): 3008,
            ("ROUEN", "KARACHI"): 6039,
            ("ROUEN", "JAKARTA"): 8819,
            ("ROUEN", "CHITTAGONG"): 7564,

            # From Burgas (base Black Sea port)
            ("BURGAS", "NINGBO"): 10600,
            ("BURGAS", "VIETNAM"): 9739,
            ("BURGAS", "ALEXANDRIA"): 848,
            ("BURGAS", "ALGIERS"): 1468,
            ("BURGAS", "BANDAR_IMAM"): 4240,
            ("BURGAS", "CASABLANCA"): 1889,
            ("BURGAS", "TUNIS"): 1115,
            ("BURGAS", "MERSIN"): 708,
            ("BURGAS", "KARACHI"): 3812,
            ("BURGAS", "JAKARTA"): 9019,
            ("BURGAS", "CHITTAGONG"): 6764,
        }
        
        # Port waiting times (days)
        self.port_delays = {
            "SANTOS": 5,      # Known for congestion
            "PARANAGUA": 5,
            "ODESSA": 5,
            "PNW": 2,
            "ROUEN": 2,
            "ALEXANDRIA": 4,
            "BANDAR_IMAM": 7, # Iranian ports often have delays
            "NINGBO": 3,
            "VIETNAM": 4
        }
        
        # Bunker prices - updated daily
        self.bunker_price = 650  # USD/MT VLSFO
        
        # Canal costs
        self.canal_costs = {
            "SUEZ": 250000,  # Approximate cost for Panamax
            "PANAMA": 200000
        }

        self.current_week = 1
        self.market_conditions = {}

    def calculate_freight(self, origin: str, destination: str, vessel_type: dict) -> float:
        """
        Calculate freight rate in USD/MT based on actual costs and market conditions.
        Returns the market freight rate for the specified route and vessel.
        """
        # Step 1: Calculate basic voyage costs
        distance = self._get_distance(origin, destination)
        if not distance:
            return None
            
        # Calculate round trip duration
        round_trip_distance = distance * 2
        sailing_days = round_trip_distance / (vessel_type["speed"] * 24)
        
        # Port time calculations
        load_days = vessel_type["capacity"] / vessel_type["load_rate"]
        discharge_days = vessel_type["capacity"] / vessel_type["discharge_rate"]
        waiting_days = (self.port_delays.get(origin, 2) + 
                       self.port_delays.get(destination, 2))
        
        total_days = sailing_days + (load_days + discharge_days + waiting_days) * 2
        
        # Step 2: Calculate actual operating costs
        # Time charter cost - daily vessel hire
        daily_rate = (vessel_type["daily_rate_pac"] 
                     if self._is_pacific_route(origin, destination)
                     else vessel_type["daily_rate_atl"])
        charter_cost = daily_rate * total_days
        
        # Bunker (fuel) cost
        bunker_cost = (vessel_type["consumption"] * total_days * self.bunker_price)
        
        # Port costs - typically charged per MT of cargo
        port_cost = vessel_type["capacity"] * 0.5 * 2  # $0.5/MT at each end
        
        # Canal costs if applicable
        canal_cost = self._get_canal_cost(origin, destination) * 2
        
        # Step 3: Calculate total cost per MT
        total_cost = charter_cost + bunker_cost + port_cost + canal_cost
        cost_per_mt = total_cost / vessel_type["capacity"]
        
        # Step 4: Apply market factors to get final rate
        # Base rate is the minimum viable rate (covers costs plus minimal return)
        base_rate = cost_per_mt * 1.05  # 5% minimum return
        
        # Market adjustment factors
        # Demand-supply balance for route
        market_factor = self.market_conditions.get((origin, destination), 1.0)
        
        # Seasonal patterns (grain harvests, weather etc)
        # Peaks during harvest seasons (weeks 15-20 and 40-45)
        season_base = math.sin(2 * math.pi * (self.current_week / 52))
        season_factor = 1.0 + (0.15 * season_base)  # ±15% seasonal variation
        
        # Vessel size specific factors
        # Larger vessels have more stable rates due to major trade routes
        # Smaller vessels more volatile due to regional trade patterns
        if vessel_type["capacity"] >= 80000:  # Panamax
            volatility = 0.15    # 15% volatility
            market_power = 0.8   # Less market pricing power
        elif vessel_type["capacity"] >= 50000:  # Supramax
            volatility = 0.20    # 20% volatility
            market_power = 0.9   # Medium market pricing power
        else:  # Handymax
            volatility = 0.25    # 25% volatility
            market_power = 1.0   # Higher market pricing power
        
        # Calculate market influence
        market_rate = base_rate * market_factor * season_factor
        
        # Add controlled randomness for market volatility
        random_factor = 1.0 + (random.uniform(-volatility, volatility) * market_power)
        
        # Final rate calculation
        final_rate = market_rate * random_factor
        
        # Ensure rate never goes below cost
        return max(base_rate, round(final_rate, 2))

    def _get_distance(self, origin: str, destination: str) -> float:
        """Get distance between ports with fallbacks"""
        # Direct lookup
        dist = self.distances.get((origin, destination))
        if dist:
            return dist
            
        # Try reverse lookup
        dist = self.distances.get((destination, origin))
        if dist:
            return dist
            
        # Regional fallbacks
        if destination == "NINGBO":
            if origin in ["SANTOS", "PARANAGUA"]:
                return 9500  # Brazil to NINGBO
            elif origin in ["ODESSA", "CONSTANTA", "NOVOROSSIYSK"]:
                return 8600   # Black Sea to NINGBO
                
        return self._estimate_distance(origin, destination)

    def _estimate_distance(self, origin: str, destination: str) -> float:
        """Estimate distance based on region"""
        # Default distances by region pair
        regional_distances = {
            ("BLACK_SEA", "MED"): 1200,
            ("BLACK_SEA", "MIDDLE_EAST"): 4200,
            ("BLACK_SEA", "ASIA"): 8600,
            ("EURUSDOPE_ATL", "MED"): 2000,
            ("SOUTH_AM", "ASIA"): 10500,
            ("SOUTH_AM", "MED"): 5000,
        }
        
        orig_region = self._get_region(origin)
        dest_region = self._get_region(destination)
        
        dist = regional_distances.get((orig_region, dest_region))
        if dist:
            return dist * 1.1  # Add 10% for indirect routing
            
        return 6000  # Default fallback

    def _get_region(self, port: str) -> str:
        """Get region for a port"""
        regions = {
            "BLACK_SEA": ["ODESSA", "CONSTANTA", "NOVOROSSIYSK"],
            "MED": ["ALEXANDRIA", "ALGIERS", "MERSIN"],
            "MIDDLE_EAST": ["BANDAR_IMAM"],
            "ASIA": ["NINGBO", "VIETNAM"],
            "SOUTH_AM": ["SANTOS", "PARANAGUA", "ROSARIO"],
            "EURUSDOPE_ATL": ["ROUEN"]
        }
        
        for region, ports in regions.items():
            if port in ports:
                return region
        return "OTHER"

    def _is_pacific_route(self, origin: str, destination: str) -> bool:
        """Determine if route is in Pacific basin"""
        pacific_ports = ["NINGBO", "VIETNAM", "PNW"]
        return (origin in pacific_ports or destination in pacific_ports)

    def _get_canal_cost(self, origin: str, destination: str) -> float:
        """Calculate canal costs if applicable"""
        # Suez Canal routes
        if (self._is_europe_to_asia(origin, destination) or 
            self._is_black_sea_to_asia(origin, destination)):
            return self.canal_costs["SUEZ"]
            
        # Panama Canal routes
        if (origin == "PNW" and destination not in ["NINGBO", "VIETNAM"]):
            return self.canal_costs["PANAMA"]
            
        return 0

    def _is_europe_to_asia(self, origin: str, destination: str) -> bool:
        """Check if route is Europe to Asia"""
        europe_ports = ["ROUEN"]
        asia_ports = ["NINGBO", "VIETNAM", "BANDAR_IMAM"]
        return (origin in europe_ports and destination in asia_ports)

    def _is_black_sea_to_asia(self, origin: str, destination: str) -> bool:
        """Check if route is Black Sea to Asia"""
        black_sea_ports = ["ODESSA", "CONSTANTA", "NOVOROSSIYSK"]
        asia_ports = ["NINGBO", "VIETNAM", "BANDAR_IMAM"]
        return (origin in black_sea_ports and destination in asia_ports)

    def update_market_conditions(self, market_conditions: dict):
        """Update market conditions from Market class"""
        self.market_conditions = market_conditions
        
    def update_bunker_price(self):
        """Update bunker prices with controlled volatility"""
        change = random.gauss(0, 10)  # Normal distribution, $10 standard deviation
        self.bunker_price = max(500, min(800, self.bunker_price + change))
        
    def set_current_week(self, week: int):
        """Update current week for seasonal calculations"""
        self.current_week = week

class Market:
    def __init__(self, game):
        self.current_week = 1
        self.year = 2024
        self.game = game
        
        # Initialize markets
        self.fob_markets: Dict[Tuple[str, str], MarketQuote] = {}
        self.freight_markets: Dict[Tuple[str, str], Dict[str, FreightQuote]] = {}
        self.freight_calculator = FreightCalculator()
        self.crop_cycles_manager = game.crop_manager

        # Initialize base FOB prices - ONLY for origin markets, not destinations
        base_fob = {
            # Corn markets with realistic spreads
            ("CORN", "SANTOS"): (215, 218),
            ("CORN", "ROSARIO"): (213, 216),
            ("CORN", "ODESSA"): (222, 225),
            ("CORN", "CONSTANTA"): (219, 223),
            ("CORN", "NOVOROSSIYSK"): (223, 226),
            ("CORN", "ROUEN"): (226, 230),
            ("CORN", "PNW"): (222, 224), 
            
            # Wheat markets 
            ("WHEAT", "SANTOS"): (221, 224),
            ("WHEAT", "ROSARIO"): (220, 223),
            ("WHEAT", "NOVOROSSIYSK"): (230, 232),  
            ("WHEAT", "ODESSA"): (228, 230),        
            ("WHEAT", "CONSTANTA"): (226, 228),
            ("WHEAT", "BURGAS"): (226, 228),
            ("WHEAT", "ROUEN"): (236, 238),         
            ("WHEAT", "PNW"): (222, 224),           
            
            # Soybean markets
            ("SOYBEAN", "SANTOS"): (379, 381),
            ("SOYBEAN", "PARANAGUA"): (378, 380),
            ("SOYBEAN", "ROSARIO"): (388, 391),
            ("SOYBEAN", "PNW"): (390, 392),
            ("SOYBEAN", "CONSTANTA"): (390, 392),
            ("SOYBEAN", "NOVOROSSIYSK"): (395, 398),
            ("SOYBEAN", "ODESSA"): (393, 395),            
        }

    
        # Initialize market prices
        for key, (bid, offer) in base_fob.items():
            self.fob_markets[key] = MarketQuote(
                bid=bid,
                offer=offer,
                bid_size=random.randint(30, 100),
                offer_size=random.randint(30, 100),
                last_price=bid,
                six_month_high=bid,  # Changed from two_month_high
                six_month_low=bid    # Changed from two_month_low
            )
                    
        # Initialize ports
        self.origins = {
            "SANTOS": Port("Santos", "Brazil", 1, 30),
            "PARANAGUA": Port("Paranagua", "Brazil", 1, 30),
            "ROSARIO": Port("Rosario", "Argentina", 1, 30),
            "PNW": Port("Pacific NW", "USA", 1, 14),
            "ODESSA": Port("Odessa", "Ukraine", 2, 30),
            "NOVOROSSIYSK": Port("Novorossiysk", "Russia", 2, 45),
            "CONSTANTA": Port("Constanta", "Romania", 1, 30),
            "ROUEN": Port("Rouen", "France", 1, 14),
            "BURGAS": Port("Burgas", "Bulgaria", 1, 30),
        }

        self.port_to_region = {
            "SANTOS": "BRAZIL_CS",
            "PARANAGUA": "BRAZIL_CS",
            "ROSARIO": "ARGENTINA",
            "NOVOROSSIYSK": "RUSSIA",
            "ODESSA": "UKRAINE",
            "CONSTANTA": "ROMANIA",
            "ROUEN": "FRANCE",
            "BURGAS": "ROMANIA",
            "PNW": "USA_PNW"
        }
        
        # Enhanced destinations with realistic groupings
        self.destinations = {
            # Mediterranean/North Africa
            "ALGIERS": Port("Algiers", "Algeria", 2, 30),
            "CASABLANCA": Port("Casablanca", "Morocco", 2, 30),
            "ALEXANDRIA": Port("Alexandria", "Egypt", 3, 180),
            "TUNIS": Port("Tunis", "Tunisia", 2, 30),
            "MERSIN": Port("Mersin", "Turkey", 2, 30),
            
            # Asia/Middle East
            "BANDAR_IMAM": Port("Bandar Imam", "Iran", 4, 360),
            "KARACHI": Port("Karachi", "Pakistan", 3, 90),
            "JAKARTA": Port("Jakarta", "Indonesia", 2, 30),
            "CHITTAGONG": Port("Chittagong", "Bangladesh", 4, 180),
            "VIETNAM": Port("Ho Chi Minh", "Vietnam", 2, 30),
            "NINGBO": Port("Various", "NINGBO", 2, 30),
        }

        self.destination_factors = {
            # Mediterranean/North Africa - Competitive markets, moderate margins
            "ALGIERS": {"base_margin": 0.03, "volatility": 0.02},
            "CASABLANCA": {"base_margin": 0.03, "volatility": 0.02},
            "ALEXANDRIA": {"base_margin": 0.04, "volatility": 0.03},
            "TUNIS": {"base_margin": 0.03, "volatility": 0.02},
            "MERSIN": {"base_margin": 0.03, "volatility": 0.02},
            
            # Premium markets - Higher margins due to quality requirements
            "NINGBO": {"base_margin": 0.05, "volatility": 0.03},
            "JAKARTA": {"base_margin": 0.05, "volatility": 0.03},
            "VIETNAM": {"base_margin": 0.6, "volatility": 0.03},
            
            # Higher risk markets - Higher margins to compensate
            "BANDAR_IMAM": {"base_margin": 0.10, "volatility": 0.04},
            "KARACHI": {"base_margin": 0.09, "volatility": 0.04},
            "CHITTAGONG": {"base_margin": 0.09, "volatility": 0.04}
        }

        # Initialize local market conditions (supply/demand factors)
        self.local_market_conditions = {dest: 1.0 for dest in self.destinations.keys()}

        # Initialize freight markets
        self._initialize_freight_markets()
        
        # Initialize destination quotes tracking
        self._dest_quotes = {}

    def _initialize_freight_markets(self):
        """Initialize freight markets with proper vessel type scaling"""
        self.freight_markets = {}
        
        vessel_types = {
            "PANAMAX": VesselType.PANAMAX,
            "SUPRAMAX": VesselType.SUPRAMAX,
            "HANDYMAX": VesselType.HANDYMAX
        }

        for origin in self.origins:
            for dest in self.destinations:
                route_key = (origin, dest)
                self.freight_markets[route_key] = {}
                
                # Calculate base rate for each vessel type independently
                for vessel_name, vessel_specs in vessel_types.items():
                    rate = self.freight_calculator.calculate_freight(
                        origin, dest, vessel_specs
                    )
                    
                    if rate:
                        self.freight_markets[route_key][vessel_name] = FreightQuote(
                            rate=rate,
                            duration_days=self._calculate_duration(origin, dest, vessel_specs),
                            vessel_size=vessel_name,
                            capacity=vessel_specs["capacity"]
                        )
    
    def _initialize_destination_markets(self):
        """Initialize market quotes for destination locations"""
        for dest in self.destinations:
            for commodity in ["WHEAT", "CORN", "SOYBEAN"]:
                self.fob_markets[(commodity, dest)] = MarketQuote(
                    bid=0,
                    offer=0,
                    bid_size=0,
                    offer_size=0
                )

    # Add vessel-specific duration calculation
    def _calculate_duration(self, origin: str, dest: str, vessel_specs: dict) -> int:
        """Calculate voyage duration including port time for specific vessel type"""
        distance = self.freight_calculator._get_distance(origin, dest)
        if not distance:
            return 0
            
        sailing_days = distance / (vessel_specs["speed"] * 24)
        loading_days = vessel_specs["capacity"] / vessel_specs["load_rate"]
        discharge_days = vessel_specs["capacity"] / vessel_specs["discharge_rate"]
        
        port_delays = (self.freight_calculator.port_delays.get(origin, 2) + 
                    self.freight_calculator.port_delays.get(dest, 2))
        
        total_days = sailing_days + loading_days + discharge_days + port_delays
        return round(total_days)
    
    def get_destination_price(self, commodity: str, origin: str, destination: str) -> Optional[dict]:
        """Calculate destination market price with tighter margins and more realistic pricing"""
        if not hasattr(self, '_dest_quotes'):
            self._dest_quotes = {}

        price_key = (commodity, origin, destination)
        
        # Get FOB quote first
        fob_quote = self.fob_markets.get((commodity, origin))
        if not fob_quote or not fob_quote.has_valid_quote():  # Added valid quote check
            return None
            
        # Calculate landed costs for all viable origins with tighter margins
        landed_costs = {}
        for potential_origin in self.origins:
            potential_fob = self.fob_markets.get((commodity, potential_origin))
            if not potential_fob or not potential_fob.has_valid_quote():  # Added valid quote check
                continue
                
            freight_quotes = self.freight_markets.get((potential_origin, destination))
            if not freight_quotes:
                continue
                
            min_freight_rate = min(quote.rate for quote in freight_quotes.values())
            landed_cost = potential_fob.offer + min_freight_rate
            
            # Reduced quality premium from 1% to 0.5%
            quality_premium = 0
            if potential_origin in ["ROUEN", "PNW"]:
                quality_premium = landed_cost * 0.005  # 0.5% premium
            
            landed_costs[potential_origin] = landed_cost + quality_premium
            
        if not landed_costs:
            return None
            
        cheapest_landed = min(landed_costs.values())
        
        this_landed = landed_costs.get(origin)
        if not this_landed:
            return None
            
        # Reduced maximum premium from 5% to 2%
        max_premium = cheapest_landed * 0.02
        if this_landed > cheapest_landed + max_premium:
            this_landed = cheapest_landed + max_premium
            
        dest_factors = self.destination_factors.get(
            destination, 
            {"base_margin": 0.02, "volatility": 0.01}  # Reduced base margin from 0.05 to 0.02
        )
        local_condition = self.local_market_conditions[destination]
        
        # Reduced risk premium scaling
        dest_port = self.destinations[destination]
        risk_premium = (dest_port.risk_level - 1) * 0.005 * this_landed  # Halved from 0.01
        
        # Reduced payment premium
        payment_premium = (dest_port.payment_delay_days / 30) * 0.002 * this_landed  # Reduced from 0.005
        
        base_price = this_landed + risk_premium + payment_premium
        
        # Apply tighter margins and increased competition
        margin = dest_factors["base_margin"] * local_condition * 0.8  # Additional 20% reduction
        mid_price = base_price * (1 + margin)
        
        # Tighter spreads
        spread = base_price * dest_factors["volatility"] * local_condition
        bid = round(mid_price - (spread / 2), 2)
        offer = round(mid_price + (spread / 2), 2)

        prev_quote = self._dest_quotes.get(price_key)
        if prev_quote:
            if abs(bid - prev_quote["bid"]) < 0.01:
                price_direction = 7
            else:
                price_direction = 4 if bid > prev_quote["bid"] else 3
        else:
            price_direction = 7
            
        new_quote = {
            "bid": bid,
            "offer": offer,
            "bid_size": random.randint(30, 100),
            "offer_size": random.randint(30, 100),
            "last_price": bid,
            "price_direction": price_direction
        }
        
        self._dest_quotes[price_key] = new_quote
        return new_quote

    
    def update_markets(self):
        """Update market prices and conditions"""
        self._update_commodity_markets()
        self._update_freight_markets()
        self._update_port_conditions()
        self._update_local_market_conditions()
        
        # Update destination quotes
        if hasattr(self, '_dest_quotes'):
            for key in list(self._dest_quotes.keys()):
                commodity, origin, destination = key
                current_quote = self.get_destination_price(commodity, origin, destination)
                if current_quote:
                    self._dest_quotes[key] = current_quote
        
        # Monthly inventory replenishment
        if self.current_week % 4 == 0:
            for quote in self.fob_markets.values():
                quote.inventory = random.randint(100000, 500000)
        
        self._advance_time()

    def _update_commodity_markets(self):
        """Update FOB market prices with realistic movements including crop cycles"""
        current_week = self.current_week
        
        for commodity in ["WHEAT", "CORN", "SOYBEAN"]:
            base_change = random.gauss(0, 1.5)
            trend = math.sin(2 * math.pi * self.current_week / 52) * 0.5
            
            for (com, origin), quote in self.fob_markets.items():
                if com == commodity:
                    # Store last price before potential updates
                    if quote.has_valid_quote():
                        quote.last_price = quote.bid
                    
                    # Get region for this origin
                    region = self.port_to_region.get(origin)
                    if region:
                        # Update crop cycle and get price factor
                        self.crop_cycles_manager.update_cycle(region, commodity, current_week)
                        price_factor = self.crop_cycles_manager.get_price_factor(region, commodity, current_week)
                        
                        # Get stock percentage and update inventory
                        stock_pct = self.crop_cycles_manager.get_stock_percentage(region, commodity)
                        quote.inventory = int(500000 * stock_pct)
                        
                        # Only update prices if we have inventory
                        if quote.inventory > 0:
                            # If prices were previously None, we need to reinitialize them
                            if quote.bid is None or quote.offer is None:
                                # Get base prices from our initial configuration
                                base_fob = {
                                    ("CORN", "SANTOS"): (215, 218),
                                    ("CORN", "ROSARIO"): (213, 216),
                                    # ... (other base prices)
                                }
                                # Initialize with base price if available, otherwise use reasonable defaults
                                if (com, origin) in base_fob:
                                    quote.bid, quote.offer = base_fob[(com, origin)]
                                else:
                                    # Use reasonable defaults based on commodity
                                    if com == "CORN":
                                        quote.bid = 215
                                        quote.offer = 218
                                    elif com == "WHEAT":
                                        quote.bid = 230
                                        quote.offer = 233
                                    elif com == "SOYBEAN":
                                        quote.bid = 380
                                        quote.offer = 383
                            
                            # Now we can safely update prices
                            local_change = base_change + random.gauss(0, 0.5) + trend
                            percent_change = (local_change / 100) * price_factor
                            quote.bid = max(0, quote.bid * (1 + percent_change))
                            quote.offer = quote.bid + random.uniform(1.0, 3.0)
                        else:
                            # Set prices to None when no inventory
                            quote.bid = None
                            quote.offer = None
                        
                        # Update historical prices - method now handles None values
                    quote.update_historical_prices(self.current_week)


    def _update_local_market_conditions(self):
        """Update local market supply/demand factors"""
        for dest in self.destinations:
            # Mean reversion to 1.0 with random shocks
            current = self.local_market_conditions[dest]
            shock = random.gauss(0, 0.05)  # Random shock with 5% standard deviation
            
            # Stronger mean reversion when further from 1.0
            reversion = (1.0 - current) * 0.1
            
            # Update with constraints
            new_condition = current + reversion + shock
            self.local_market_conditions[dest] = max(0.8, min(1.2, new_condition))

            # Add significant market events
            if abs(new_condition - current) > 0.1:
                event = "shortage" if new_condition > current else "oversupply"
                self.destinations[dest].add_status(f"Market {event} reported")

    def _update_freight_markets(self):
        """Update freight rates with market correlation"""
        # Update bunker price first
        self.freight_calculator.update_bunker_price()
        
        # Generate market-wide movement
        base_freight_change = random.gauss(0, 0.3)
        
        # Seasonal factor (higher rates during peak seasons)
        season_factor = 1 + 0.5 * math.sin(2 * math.pi * self.current_week / 52)
        
        for routes in self.freight_markets.values():
            for quote in routes.values():
                quote.last_rate = quote.rate
                # Individual route variation plus market correlation
                route_change = base_freight_change + random.gauss(0, 0.2)
                adjusted_change = route_change * season_factor
                
                # Ensure minimum viable freight rate
                min_rate = 25  # Minimum viable freight rate
                quote.rate = max(min_rate, quote.rate + adjusted_change)

    def _update_port_conditions(self):
        """Update port congestion and weather conditions"""
        for port in list(self.origins.values()) + list(self.destinations.values()):
            old_congestion = port.congestion_level
            
            # Mean reverting congestion with seasonal factors
            season_factor = 1 + 0.5 * math.sin(2 * math.pi * self.current_week / 52)
            target_congestion = 30 * season_factor  # Base congestion level
            
            congestion_change = random.randint(-5, 5)
            port.congestion_level = max(0, min(100,
                port.congestion_level + (target_congestion - port.congestion_level) * 0.1 + congestion_change
            ))
            
            # Update weather delays with seasonal impact
            weather_change = random.randint(-1, 1)
            port.weather_delay = max(0, min(5,
                port.weather_delay + weather_change * season_factor
            ))
            
            # Add significant status updates
            if port.congestion_level > old_congestion + 20:
                port.add_status(f"Severe congestion: {port.congestion_level}%")
            elif port.weather_delay > 2:
                port.add_status(f"Weather delays: {port.weather_delay} days")

    def _advance_time(self):
        """Advance game time"""
        self.current_week += 1
        if self.current_week > 52:
            self.current_week = 1
            self.year += 1

    def get_market_status(self, commodity: str = None, origin: str = None) -> Dict:
        """Get current market status including crop cycle information"""
        status = {
            "date": f"Week {self.current_week}, {self.year}",
            "prices": {},
            "freight_rates": {},
            "crop_cycles": {}  # Add new section for crop cycles
        }

        # Filter market prices
        for (com, orig), quote in self.fob_markets.items():
            if (not commodity or com == commodity) and (not origin or orig == origin):
                region = self.port_to_region.get(orig)
                status["prices"][(com, orig)] = {
                    "bid": quote.bid,
                    "offer": quote.offer,
                    "bid_size": quote.bid_size,
                    "offer_size": quote.offer_size,
                    "direction": quote.price_direction()
                }
                
                if region:
                    status["crop_cycles"][(com, orig)] = {
                        "harvest_progress": self.crop_cycles_manager.get_harvest_progress(region, com),
                        "stock_percentage": self.crop_cycles_manager.get_stock_percentage(region, com)
                    }

        # Add freight rates (existing code)
        if origin:
            for dest in self.destinations:
                if (origin, dest) in self.freight_markets:
                    status["freight_rates"][dest] = {
                        vessel: {
                            "rate": quote.rate,
                            "duration": quote.duration_days,
                            "direction": 4 if quote.rate < quote.last_rate else 3
                        }
                        for vessel, quote in self.freight_markets[(origin, dest)].items()
                    }

        return status

    def get_route_status(self, origin: str, destination: str) -> Dict:
        """Get detailed status for a specific route"""
        if (origin, destination) not in self.freight_markets:
            return None
            
        route_info = {
            "distance": self.freight_calculator._get_distance(origin, destination),
            "origin_delays": self.origins[origin].get_total_delay(),
            "destination_delays": self.destinations[destination].get_total_delay(),
            "vessel_options": {}
        }
        
        # Add vessel-specific information
        for vessel, quote in self.freight_markets[(origin, destination)].items():
            route_info["vessel_options"][vessel] = {
                "rate": quote.rate,
                "duration": quote.duration_days,
                "capacity": quote.capacity
            }
        
        return route_info

class StorageManager:
    """Manages all storage facilities in the game"""
    def __init__(self, game):  # Changed to accept game instance
        self.facilities: Dict[str, StorageFacility] = self._initialize_facilities()
        self.handling_history: List[Dict] = []
        self.last_cost_week = 0
        self.game = game  # Store game reference
        
    def _initialize_facilities(self) -> Dict[str, StorageFacility]:
        """Initialize storage facilities with realistic capacities and costs"""
        facilities = {
            # South America - Large export facilities
            "SANTOS": StorageFacility(
                name="Santos Terminal",
                total_capacity=1_000_000,
                available_capacity=1_000_000,
                monthly_cost=1.25,        # USD/MT/month
                handling_cost=1.2,       # USD/MT
                min_throughput=50_000,   # MT/month
                max_intake_rate=15_000,  # MT/day
                max_outtake_rate=15_000
            ),
            "PARANAGUA": StorageFacility(
                name="Paranagua Silos",
                total_capacity=800_000,
                available_capacity=800_000,
                monthly_cost=1.5,
                handling_cost=1.25,
                min_throughput=40_000,
                max_intake_rate=12_000,
                max_outtake_rate=12_000
            ),
            "ROSARIO": StorageFacility(
                name="Rosario Terminal",
                total_capacity=600_000,
                available_capacity=600_000,
                monthly_cost=1.5,
                handling_cost=1.5,
                min_throughput=30_000,
                max_intake_rate=10_000,
                max_outtake_rate=10_000
            ),
            
            # Black Sea - Competitive rates
            "ODESSA": StorageFacility(
                name="Odessa Terminal",
                total_capacity=600_000,
                available_capacity=600_000,
                monthly_cost=1.5,
                handling_cost=1.5,
                min_throughput=30_000,
                max_intake_rate=10_000,
                max_outtake_rate=10_000
            ),
            "NOVOROSSIYSK": StorageFacility(
                name="Novorossiysk Terminal",
                total_capacity=700_000,
                available_capacity=700_000,
                monthly_cost=1.5,
                handling_cost=1.5,
                min_throughput=35_000,
                max_intake_rate=12_000,
                max_outtake_rate=12_000
            ),
            "CONSTANTA": StorageFacility(
                name="Constanta Terminal",
                total_capacity=500_000,
                available_capacity=500_000,
                monthly_cost=0.8,
                handling_cost=1,
                min_throughput=25_000,
                max_intake_rate=8_000,
                max_outtake_rate=8_000
            ),
            "ALEXANDRIA": StorageFacility(
                name="Alexandria Silos",
                total_capacity=500_000,
                available_capacity=500_000,
                monthly_cost=1.5,
                handling_cost=1.5,
                min_throughput=25_000,
                max_intake_rate=8_000,
                max_outtake_rate=8_000
            ),
            "ALGIERS": StorageFacility(
                name="Algiers Terminal",
                total_capacity=400_000,
                available_capacity=400_000,
                monthly_cost=1.2,
                handling_cost=1,
                min_throughput=20_000,
                max_intake_rate=7_000,
                max_outtake_rate=7_000
            ),
            "BANDAR_IMAM": StorageFacility(
                name="Bandar Imam Terminal",
                total_capacity=300_000,
                available_capacity=300_000,
                monthly_cost=3.0,
                handling_cost=2.0,
                min_throughput=15_000,
                max_intake_rate=5_000,
                max_outtake_rate=5_000
            ),
            "MERSIN": StorageFacility(
                name="Toros Terminal",
                total_capacity=400_000,
                available_capacity=400_000,
                monthly_cost=1.25,
                handling_cost=1,
                min_throughput=20_000,
                max_intake_rate=7_000,
                max_outtake_rate=7_000
            ),
            "ROUEN": StorageFacility(
                name="Rouen Terminal",
                total_capacity=450_000,
                available_capacity=450_000,
                monthly_cost=1.2,
                handling_cost=0.8,
                min_throughput=25_000,
                max_intake_rate=8_000,
                max_outtake_rate=8_000
            ),
            "BURGAS": StorageFacility(
                name="Burgas Terminal",
                total_capacity=400_000,
                available_capacity=400_000,
                monthly_cost=1.2,
                handling_cost=1,
                min_throughput=20_000,
                max_intake_rate=7_000,
                max_outtake_rate=7_000
            ),
            "PNW": StorageFacility(
                name="Pacific Northwest Terminal",
                total_capacity=600_000,
                available_capacity=600_000,
                monthly_cost=0.5,
                handling_cost=1,
                min_throughput=30_000,
                max_intake_rate=10_000,
                max_outtake_rate=10_000
            ),

            "CHITTAGONG": StorageFacility(
                name="Chittagong Terminal",
                total_capacity=300_000,
                available_capacity=300_000,
                monthly_cost=2,
                handling_cost=1,
                min_throughput=15_000,
                max_intake_rate=5_000,
                max_outtake_rate=5_000
            ),
            "VIETNAM": StorageFacility(
                name="Vietnam Terminal",
                total_capacity=400_000,
                available_capacity=400_000,
                monthly_cost=1.5,
                handling_cost=1,
                min_throughput=20_000,
                max_intake_rate=7_000,
                max_outtake_rate=7_000
            ),
            "JAKARTA": StorageFacility(
                name="Jakarta Terminal",
                total_capacity=350_000,
                available_capacity=350_000,
                monthly_cost=1.3,
                handling_cost=0.75,
                min_throughput=18_000,
                max_intake_rate=6_000,
                max_outtake_rate=6_000
            ),
            "CASABLANCA": StorageFacility(
                name="Casablanca Terminal",
                total_capacity=350_000,
                available_capacity=350_000,
                monthly_cost=1,
                handling_cost=1,
                min_throughput=18_000,
                max_intake_rate=6_000,
                max_outtake_rate=6_000
            ),
            "NINGBO": StorageFacility(
                name="Ningbo Terminal",
                total_capacity=1150_000,
                available_capacity=1150_000,
                monthly_cost=1.2,
                handling_cost=1.25,
                min_throughput=30_000,
                max_intake_rate=10_000,
                max_outtake_rate=10_000
            )
        }
        
        return facilities
    
    def store_grain(self, location: str, commodity: str, quantity: int) -> Tuple[bool, float]:
        """Attempt to store grain at location, returns success and total cost"""
        if location not in self.facilities:
            return False, 0
            
        facility = self.facilities[location]
        if not facility.can_accept(quantity):
            return False, 0
            
        # Calculate immediate handling cost
        handling_cost = facility.handling_cost * quantity
        
        # Store the grain
        if facility.store_grain(commodity, quantity):
            # Record the handling operation
            self.handling_history.append({
                "timestamp": datetime.now(),
                "location": location,
                "commodity": commodity,
                "quantity": quantity,
                "operation": "STORE",
                "cost": handling_cost
            })
            return True, handling_cost
        return False, 0
    
    def remove_grain(self, location: str, commodity: str, quantity: int) -> Tuple[bool, float]:
        """Remove grain and calculate final storage costs"""
        if location not in self.facilities:
            return False, 0
            
        facility = self.facilities[location]
        handling_cost = facility.handling_cost * quantity
        
        # Calculate prorated storage cost for partial period
        weeks_since_last_charge = (self.game.market.current_week - self.last_cost_week) % 4
        if weeks_since_last_charge > 0:
            days = weeks_since_last_charge * 7
            storage_cost = facility.calculate_storage_cost(quantity, days)
            handling_cost += storage_cost
        
        if facility.remove_grain(commodity, quantity):
            self.handling_history.append({
                "timestamp": datetime.now(),
                "location": location,
                "commodity": commodity,
                "quantity": quantity,
                "operation": "REMOVE",
                "cost": handling_cost,
                "includes_storage": weeks_since_last_charge > 0
            })
            return True, handling_cost
        return False, 0
    
    def get_storage_costs(self, location: str, quantity: int, days: int) -> float:
        """Get storage costs for a period at location"""
        if location not in self.facilities:
            return 0
        return self.facilities[location].calculate_storage_cost(quantity, days)
    
    def get_facility_status(self, location: str) -> Dict:
        """Get current status of storage facility"""
        if location not in self.facilities:
            return None
            
        facility = self.facilities[location]
        return {
            "name": facility.name,
            "total_capacity": facility.total_capacity,
            "available_capacity": facility.available_capacity,
            "utilization": (facility.total_capacity - facility.available_capacity) / facility.total_capacity,
            "monthly_cost": facility.monthly_cost,
            "handling_cost": facility.handling_cost,
            "inventory": facility.current_inventory.copy(),
            "max_intake_rate": facility.max_intake_rate,
            "max_outtake_rate": facility.max_outtake_rate
        }

    def get_all_storage_positions(self) -> Dict[str, Dict]:
        """Get all current storage positions across facilities"""
        positions = {}
        for location, facility in self.facilities.items():
            if facility.current_inventory:
                positions[location] = {
                    "inventory": facility.current_inventory.copy(),
                    "monthly_cost": facility.monthly_cost,
                    "handling_cost": facility.handling_cost
                }
        return positions

    def get_storage_history(self, days: int = 30) -> List[Dict]:
        """Get storage handling history for specified period"""
        cutoff = datetime.now() - timedelta(days=days)
        return [op for op in self.handling_history if op["timestamp"] > cutoff]

    def update_storage_costs(self, current_week: int) -> Dict[str, float]:
        """Calculate storage costs every 4 weeks"""
        costs = {}
        
        # Only process on weeks divisible by 4 (monthly)
        if current_week % 4 == 0 and current_week != self.last_cost_week:
            for location, facility in self.facilities.items():
                monthly_cost = 0
                if facility.current_inventory:
                    for commodity, quantity in facility.current_inventory.items():
                        # Calculate one month's worth of storage cost
                        monthly_cost += quantity * facility.monthly_cost
                    
                    if monthly_cost > 0:
                        costs[location] = monthly_cost
                        
            self.last_cost_week = current_week
        return costs

    def check_throughput_requirements(self, location: str) -> bool:
        """Check if minimum throughput requirements are being met"""
        if location not in self.facilities:
            return True
            
        facility = self.facilities[location]
        # Get last 30 days of handling
        recent_handling = sum(
            op["quantity"] for op in self.handling_history
            if op["location"] == location and 
            op["timestamp"] > datetime.now() - timedelta(days=30)
        )
        
        return recent_handling >= facility.min_throughput

    def get_storage_analytics(self, location: str) -> Dict:
        """Get detailed analytics for a storage facility"""
        if location not in self.facilities:
            return None
            
        facility = self.facilities[location]
        recent_ops = [op for op in self.handling_history 
                     if op["location"] == location and 
                     op["timestamp"] > datetime.now() - timedelta(days=30)]
        
        return {
            "utilization_rate": 1 - (facility.available_capacity / facility.total_capacity),
            "monthly_throughput": sum(op["quantity"] for op in recent_ops),
            "handling_costs": sum(op["cost"] for op in recent_ops),
            "inventory_value": facility.current_inventory.copy(),
            "throughput_requirement_met": self.check_throughput_requirements(location)
        }

class TradeRecap:
    """Interactive trade recap popup with terminal-style UI"""
    def __init__(self):
        self.visible = False
        self.animation_progress = 0.0
        self.trade_data = None
        self.scroll_offset = 0
        self.time = 0
        
    def show(self, trade):
        """Prepare and show trade recap"""
        self.visible = True
        self.animation_progress = 0.0
        self.trade_data = trade
        self.scroll_offset = 0
    
    def hide(self):
        """Hide the recap window"""
        self.visible = False
        self.trade_data = None
    
    def update(self):
        """Update animation and state"""
        if not self.visible:
            self.animation_progress = max(0.0, self.animation_progress - 0.2)
            return

        self.animation_progress = min(1.0, self.animation_progress + 0.2)
        self.time += 1

        # Handle keyboard input
        if pyxel.btnp(pyxel.KEY_X):
            self.hide()
            
        # Update scroll offset with arrow keys
        if pyxel.btn(pyxel.KEY_UP):
            self.scroll_offset = max(0, self.scroll_offset - 2)
        if pyxel.btn(pyxel.KEY_DOWN):
            self.scroll_offset = min(200, self.scroll_offset + 2)  # Adjust max based on content

    def _format_number(self, number: float, decimals: int = 1) -> str:
        """Format numbers consistently, handling None values"""
        if number is None:  # Changed from just checking isinstance
            return " - "    # Return dashes instead of "None"
        if isinstance(number, (int, float)):
            return f"{round(number, decimals):,.{decimals}f}"
        return str(number)

    def draw(self):
        """Draw the trade recap popup"""
        if self.animation_progress <= 0 or not self.trade_data:
            return

        # Calculate centered position with animation
        window_width = 300
        window_height = 280
        x = (450 - window_width) // 2
        y = (450 - window_height) // 2
        
        # Apply slide-in animation from top
        current_y = y + (1 - self.animation_progress) * (-window_height)
        
        # Draw window background with border
        pyxel.rect(x, current_y, window_width, window_height, 1)
        pyxel.rectb(x, current_y, window_width, window_height, 2)
        
        # Draw title bar
        title = "TRADE RECAP"
        title_x = x + (window_width - len(title) * 4) // 2
        pyxel.rect(x, current_y, window_width, 10, 2)
        pyxel.text(title_x, current_y + 2, title, 7)
        
        # Start content area
        content_y = current_y + 15 - self.scroll_offset
        
        # Helper function to draw a section
        def draw_section(title, content, color=7):
            nonlocal content_y
            pyxel.text(x + 10, content_y, title, 8)
            content_y += 8
            pyxel.text(x + 20, content_y, content, color)
            content_y += 12
        
        # Draw trade information sections
        draw_section("ROUTE",
                    f"{self.trade_data.origin} -> {self.trade_data.destination}")
        draw_section("COMMODITY",
                    f"{self.trade_data.commodity} - {self._format_number(self.trade_data.quantity/1000, 1)}K MT")
        draw_section("VESSEL",
                    f"{self.trade_data.vessel_type}")
        
        # Add separator
        content_y += 2
        pyxel.line(x + 10, content_y, x + window_width - 10, content_y, 5)
        content_y += 6

        # Draw prices section
        fob_color = 7
        draw_section("FOB PRICE",
                    f"${self._format_number(self.trade_data.fob_price, 2)}/MT", fob_color)
        draw_section("FREIGHT RATE",
                    f"${self._format_number(self.trade_data.freight_rate, 2)}/MT", fob_color)
        
        # Add separator
        content_y += 2
        pyxel.line(x + 10, content_y, x + window_width - 10, content_y, 5)
        content_y += 6

        # Calculate and display unit economics
        revenue_per_mt = self.trade_data.revenue / self.trade_data.quantity if self.trade_data.quantity > 0 else 0
        profit = self.trade_data.revenue - self.trade_data.total_cost
        profit_per_mt = profit / self.trade_data.quantity if self.trade_data.quantity > 0 else 0
        roi = (profit / self.trade_data.total_cost * 100) if self.trade_data.total_cost > 0 else 0
        
        # Draw results section with color coding
        profit_color = 4 if profit > 0 else 3
        draw_section("SALE PRICE",
                    f"${self._format_number(revenue_per_mt, 2)}/MT", profit_color)
        draw_section("TOTAL P/L",
                    f"${self._format_number(profit, 0)}", profit_color)
        draw_section("MARGIN",
                    f"${self._format_number(profit_per_mt, 2)}/MT", profit_color)
        draw_section("ROI",
                    f"{self._format_number(roi, 1)}%", profit_color)

        # Draw timing information
        content_y += 2
        pyxel.line(x + 10, content_y, x + window_width - 10, content_y, 5)
        content_y += 6
        
        draw_section("EXECUTION",
                    f"Week {self.trade_data.execution_week}/{self.trade_data.execution_year}")
        draw_section("ARRIVAL",
                    f"Week {self.trade_data.arrival_week}/{self.trade_data.arrival_year}")

        # Draw exit instruction with pulsing effect
        exit_text = "PRESS X TO CLOSE"
        exit_color = 7 if (self.time // 15) % 2 == 0 else 5
        exit_x = x + (window_width - len(exit_text) * 4) // 2
        pyxel.text(exit_x, current_y + window_height - 10, exit_text, exit_color)

        # Draw scroll indicators if needed
        if self.scroll_offset > 0:
            pyxel.tri(x + window_width - 10, current_y + 15,
                     x + window_width - 15, current_y + 10,
                     x + window_width - 5, current_y + 10, 7)
        if self.scroll_offset < 200:  # Adjust based on content height
            pyxel.tri(x + window_width - 10, current_y + window_height - 15,
                     x + window_width - 15, current_y + window_height - 10,
                     x + window_width - 5, current_y + window_height - 10, 7)

class PriceGraph:
    """Interactive price graph popup with terminal-style visualization"""
    def __init__(self):
        self.visible = False
        self.animation_progress = 0.0
        self.market_data = None
        self.title = ""
        
    def show(self, market_data, commodity, port):
        """Prepare and show price graph for selected market"""
        if not market_data or not market_data.has_sufficient_history():
            return False
            
        # Filter out any None values from history
        valid_history = [(week, bid, offer) for week, bid, offer in market_data.price_history 
                        if bid is not None and offer is not None]
        
        if len(valid_history) < 2:
            return False
            
        self.visible = True
        self.animation_progress = 0.0
        self.market_data = market_data
        self.title = f"{commodity} - {port}"
        return True
    
    def hide(self):
        """Hide the graph window"""
        self.visible = False
        self.market_data = None
        
    def update(self):
        """Update animation and handle input"""
        if not self.visible:
            self.animation_progress = max(0.0, self.animation_progress - 0.2)
            return

        self.animation_progress = min(1.0, self.animation_progress + 0.2)
        
        if pyxel.btnp(pyxel.KEY_X):
            self.hide()
            
    def draw(self):
        """Draw the price graph popup with price history"""
        if self.animation_progress <= 0 or not self.market_data:
            return

        # Calculate window dimensions
        window_width = 300
        window_height = 200
        x = (450 - window_width) // 2
        y = (450 - window_height) // 2
        
        # Apply slide-in animation
        current_y = y + (1 - self.animation_progress) * (-window_height)
        
        # Draw window background
        pyxel.rect(x, current_y, window_width, window_height, 1)
        pyxel.rectb(x, current_y, window_width, window_height, 2)
        
        # Draw title bar with enhanced information
        pyxel.rect(x, current_y, window_width, 10, 2)
        commodity, location = self.title.split(" - ")
        title = f"FOB {commodity} {location}"
        title_x = x + (window_width - len(title) * 4) // 2
        pyxel.text(title_x, current_y + 2, title, 7)
        
        # Draw legend
        legend_y = current_y + 2
        pyxel.text(x + window_width - 80, legend_y, "Bid", 4)  # Green for bid
        pyxel.text(x + window_width - 40, legend_y, "Offer", 3)  # Red for offer
        
        # Calculate graph dimensions - adjusted to leave room for labels
        graph_x = x + 40  # More space for y-axis label
        graph_y = current_y + 30  # More space for title and legend
        graph_width = window_width - 60
        graph_height = window_height - 60  # More space for x-axis label
        
        # Draw graph border and grid
        pyxel.rectb(graph_x, graph_y, graph_width, graph_height, 5)
        
        # Draw axis labels
        y_label = "PRICE $/MT"
        x_label = "Week"
        # Y-axis label (vertical)
        for i, char in enumerate(y_label):
            pyxel.text(x + graph_width + 45, ((graph_y+20) + i * 8), char, 8)
        # X-axis label (horizontal)
        pyxel.text(graph_x + (graph_width - len(x_label) * 4) // 2, 
                graph_y + graph_height + 15, x_label, 8)
        
        # Get price range for scaling
        history = self.market_data.price_history
        all_prices = [p for _, bid, offer in history for p in (bid, offer)]
        min_price = min(all_prices) * 0.995  # Add 0.5% padding
        max_price = max(all_prices) * 1.005
        
        # Draw price axis labels and grid lines
        num_labels = 6
        for i in range(num_labels):
            # Calculate price for this label
            price = min_price + (max_price - min_price) * (1 - i/(num_labels-1))
            label_y = graph_y + (i * (graph_height-1))/(num_labels-1)
            price_str = f"${price:.2f}"
            pyxel.text(x + 8, label_y - 2, price_str, 7)
            
            # Draw horizontal grid line
            pyxel.line(graph_x, label_y, graph_x + graph_width - 1, label_y, 2)
        
        # Draw week labels with less crowding
        weeks = [week for week, _, _ in history]
        num_weeks = len(weeks)
        if num_weeks >= 2:
            # Show every 4th week to avoid crowding
            for i, week in enumerate(weeks):
                if i % 2 == 0:
                    x_pos = graph_x + (i * (graph_width-1))/(num_weeks-1)
                    pyxel.text(x_pos - 6, graph_y + graph_height + 5, str(week), 7)
        
        # Draw price history lines
        if num_weeks >= 2:
            # Draw bid line (green)
            for i in range(num_weeks - 1):
                x1 = graph_x + (i * (graph_width-1))/(num_weeks-1)
                x2 = graph_x + ((i+1) * (graph_width-1))/(num_weeks-1)
                y1 = graph_y + (graph_height-1) * (1 - (history[i][1] - min_price)/(max_price - min_price))
                y2 = graph_y + (graph_height-1) * (1 - (history[i+1][1] - min_price)/(max_price - min_price))
                pyxel.line(x1, y1, x2, y2, 4)
                
            # Draw offer line (red)
            for i in range(num_weeks - 1):
                x1 = graph_x + (i * (graph_width-1))/(num_weeks-1)
                x2 = graph_x + ((i+1) * (graph_width-1))/(num_weeks-1)
                y1 = graph_y + (graph_height-1) * (1 - (history[i][2] - min_price)/(max_price - min_price))
                y2 = graph_y + (graph_height-1) * (1 - (history[i+1][2] - min_price)/(max_price - min_price))
                pyxel.line(x1, y1, x2, y2, 3)
        
        # Draw exit instruction with proper spacing
        exit_text = "PRESS X TO CLOSE"
        exit_x = x + 2
        pyxel.text(exit_x, current_y + 2, exit_text,  # Moved up by increasing the subtraction
                7 if (pyxel.frame_count // 15) % 2 == 0 else 5)

class Game:
    def __init__(self):
        # Initialize Pyxel with custom colors
        pyxel.init(450, 450, title="Commodity Trading Sim", display_scale=2)
        
        # Define custom terminal-inspired colors
        custom_colors = [
            0x0C1117,  # 0: Dark background
            0x1A2632,  # 1: Panel background
            0x2C3D4F,  # 2: Lighter panel
            0xFF3B3B,  # 3: Negative/Down (red)
            0x00C853,  # 4: Positive/Up (green)
            0x2196F3,  # 5: Info blue
            0xFFB300,  # 6: Warning/Alert
            0xE0E0E0,  # 7: Primary text
            0x90A4AE,  # 8: Secondary text
            0x4CAF50,  # 9: Success
            0xFF9800,  # 10: Active/Selected
            0x448AFF,  # 11: Links/Navigation
            0x8E24AA,  # 12: Special highlights
            0xF44336,  # 13: Critical/Error
            0x00BCD4,  # 14: Info/Status
            0x78909C   # 15: Disabled/Muted
        ]
        
        pyxel.colors.from_list(custom_colors)
        
        # Initialize game state
        self.crop_manager = CropCycleManager()
        self.market = Market(self)
        self.storage_manager = StorageManager(self)
        self.capital = 100_000_000
        self.TENDER_DEFAULT_PENALTY = 5_000_000
        self.initial_capital = self.capital
        self.active_trades: List[Trade] = []
        self.completed_trades: List[Trade] = []
        self.storage_positions: List[StorageTransaction] = []
        self.selected_freight_origin = "SANTOS"  # Default selection
        self.selected_destination_idx = 0
        self.selected_vessel_idx = 0
        self.vessel_types = ["HANDYMAX", "SUPRAMAX", "PANAMAX"]
        self.selected_storage_facility = "SANTOS"
        self.trade_recap = TradeRecap()
        self.selected_storage_row = 0 
        self.futures_manager = FuturesManager(self)
        self.futures_ui = FuturesUI(self)
        

        self.tender_manager = TenderManager(self)
        self.show_tender_results = False
        self.tender_results = None
        self.selected_tender_idx = 0
        self.current_tender_offer = {
            'num_vessels': 1,
            'origin': None,
            'price': 0.0
        }
        self.tender_deliveries: List[TenderDelivery] = []  # Track tender deliveries
        self.tender_penalties: float = 0  # Track accumulated penalties
        self.tender_results_queue = []  # Queue of tender results to display
        self.pending_tender_results = []  # Queue of tender results to display
        self.current_tender_result = None

        # UI state
        self.view_mode = "MARKET"  # MARKET, FREIGHT, TRADES, STORAGE, ANALYSIS
        self.selected_row = 0
        self.selected_commodity = "CORN"
        self.selected_origin = "SANTOS"
        self.selected_destination = "ALGIERS"
        self.selected_vessel = "PANAMAX"
        self.scroll_offset = 0  # This is your existing scroll offset for facilities
        self.storage_scroll_offset = 0  
        self.flash_messages: List[Tuple[str, int, int]] = []

        self.price_graph = PriceGraph()
        self.futures_graph = FuturesCurveGraph()
        
        # Start game loop
        pyxel.run(self.update, self.draw)

    def _format_number(self, number: float, decimals: int = 1) -> str:
        """Format numbers to avoid floating point artifacts"""
        if isinstance(number, (int, float)):
            return f"{round(number, decimals):,.{decimals}f}"
        return str(number)
    
    def _handle_scrolling(self):
        """Handle scrolling for long lists"""
        if self.view_mode == "MARKET":
            visible_rows = (170 - 20) // 8  # Adjusted for market view height
            total_rows = len(self.market.fob_markets)
        elif self.view_mode == "FREIGHT":
            visible_rows = (380 - 60) // 10  # Adjusted for freight view height
            total_rows = sum(len(vessels) for vessels in self.market.freight_markets.values())
        elif self.view_mode == "STORAGE":
            visible_rows = (170 - 20) // 10  # Adjusted for storage view height
            total_rows = len(self.storage_manager.facilities)
        else:
            return
            
        # Adjust scroll offset based on selection
        if self.selected_row < self.scroll_offset:
            self.scroll_offset = self.selected_row
        elif self.selected_row >= self.scroll_offset + visible_rows:
            self.scroll_offset = min(total_rows - visible_rows, 
                                self.selected_row - visible_rows + 1)
        
        # Clamp scroll offset
        max_scroll = max(0, total_rows - visible_rows)
        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

    def _update_selection(self):
        """Update selected trade parameters based on current row"""
        keys = list(self.market.fob_markets.keys())
        if 0 <= self.selected_row < len(keys):
            self.selected_commodity, self.selected_origin = keys[self.selected_row]

    def update_trades(self):
        """Update status of all active trades"""
        for trade in self.active_trades[:]:  # Use slice copy to allow modification during iteration
            if trade.status == TradeStatus.SAILING:
                # Check if arrived
                freight_quote = self.market.freight_markets[(trade.origin, trade.destination)][trade.vessel_type]
                total_voyage_days = freight_quote.duration_days + \
                                self.market.origins[trade.origin].get_total_delay() + \
                                self.market.destinations[trade.destination].get_total_delay()
                
                voyage_weeks = math.ceil(total_voyage_days / 7)
                current_week = self.market.current_week + (self.market.year - trade.execution_year) * 52
                execution_week = trade.execution_week + (trade.execution_year - trade.execution_year) * 52
                
                if current_week - execution_week >= voyage_weeks:
                    trade.status = TradeStatus.DELIVERED
                    trade.arrival_week = self.market.current_week
                    trade.arrival_year = self.market.year
                    self.flash_message(f"{trade.commodity} cargo arrived at {trade.destination}", 4)
                    
            elif trade.status == TradeStatus.DELIVERED:
                # Check if payment received
                dest_port = self.market.destinations[trade.destination]
                payment_weeks = math.ceil(dest_port.payment_delay_days / 7)
                weeks_since_arrival = (self.market.current_week + (self.market.year - trade.arrival_year) * 52) - \
                                    (trade.arrival_week + (trade.arrival_year - trade.arrival_year) * 52)
                
                if weeks_since_arrival >= payment_weeks:
                    # Get final destination price for revenue calculation
                    dest_quote = self.market.get_destination_price(
                        trade.commodity,
                        trade.origin,
                        trade.destination
                    )
                    
                    if dest_quote:
                        # Use bid price at destination as revenue
                        trade.revenue = dest_quote["bid"] * trade.quantity
                        trade.estimated_profit = trade.revenue - trade.total_cost
                    
                    trade.status = TradeStatus.COMPLETED
                    self.completed_trades.append(trade)
                    self.active_trades.remove(trade)
                    
                    # Add revenue to capital
                    self.capital += trade.revenue
                    
                    # THIS CAN BE COMMENTED OUT 
                    # self.print_trade_economics(trade)
                    
                    self.trade_recap.show(trade)
                
                    # Still flash the message
                    roi = (trade.estimated_profit / trade.total_cost) * 100 if trade.total_cost > 0 else 0
                    self.flash_message(
                        f"Trade completed - ROI: {self._format_number(roi, 1)}% (${self._format_number(trade.estimated_profit, 0)})",
                        4 if trade.estimated_profit > 0 else 3
                    )

    # Add this method to the Game class to print detailed trade economics
    def print_trade_economics(self, trade: Trade):
        """Print detailed trade economics to terminal"""
        print("\n" + "="*80)
        print(f"TRADE ECONOMICS SUMMARY - {trade.commodity}")
        print("="*80)
        
        # Basic trade info
        print(f"\nROUTE: {trade.origin} -> {trade.destination}")
        print(f"VESSEL: {trade.vessel_type}")
        print(f"QUANTITY: {self._format_number(trade.quantity, 0)} MT")
        print(f"\nTIMING:")
        print(f"Execution: Week {trade.execution_week}/{trade.execution_year}")
        print(f"Arrival: Week {trade.arrival_week}/{trade.arrival_year}")
        
        # Costs breakdown
        print(f"\nCOSTS:")
        print(f"FOB Price: ${self._format_number(trade.fob_price, 2)}/MT")
        print(f"Freight Rate: ${self._format_number(trade.freight_rate, 2)}/MT")
        print(f"Total Unit Cost: ${self._format_number(trade.fob_price + trade.freight_rate, 2)}/MT")
        
        print(f"\nTOTAL COSTS:")
        print(f"FOB Cost: ${self._format_number(trade.fob_cost, 0)}")
        print(f"Freight Cost: ${self._format_number(trade.freight_cost, 0)}")
        print(f"Total Cost: ${self._format_number(trade.total_cost, 0)}")
        
        # Revenue calculations
        revenue_per_mt = trade.revenue / trade.quantity if trade.quantity > 0 else 0
        print(f"\nREVENUE:")
        print(f"Sale Price: ${self._format_number(revenue_per_mt, 2)}/MT")
        print(f"Total Revenue: ${self._format_number(trade.revenue, 0)}")
        
        # Profitability
        gross_margin = trade.revenue - trade.total_cost
        margin_per_mt = gross_margin / trade.quantity if trade.quantity > 0 else 0
        roi = (gross_margin / trade.total_cost * 100) if trade.total_cost > 0 else 0
        
        print(f"\nPROFITABILITY:")
        print(f"Gross Margin: ${self._format_number(gross_margin, 0)}")
        print(f"Margin per MT: ${self._format_number(margin_per_mt, 2)}/MT")
        print(f"ROI: {self._format_number(roi, 1)}%")
        print("="*80 + "\n")

    def execute_trade(self):
        """Execute a new trade"""
        # Get market quotes
        fob_quote = self.market.fob_markets.get((self.selected_commodity, self.selected_origin))
        if not fob_quote:
            self.flash_message("Invalid trade route!", 13)
            return
            
        # Add explicit zero inventory check
        if fob_quote.inventory <= 0:
            self.flash_message("No inventory available!", 13)
            return
        
        # Add safety check for invalid quotes
        if not fob_quote.bid or not fob_quote.offer:
            self.flash_message("No valid market quote!", 13)
            return
        
        freight_quotes = self.market.freight_markets.get((self.selected_origin, self.selected_destination))
        if not freight_quotes or self.selected_vessel not in freight_quotes:
            self.flash_message("Invalid trade route!", 13)
            return
            
        freight_quote = freight_quotes[self.selected_vessel]
        
        # Calculate trade details
        quantity = min(freight_quote.capacity, fob_quote.inventory)
        fob_cost = fob_quote.offer * quantity
        freight_cost = freight_quote.rate * quantity
        total_cost = fob_cost + freight_cost
        
        # Validate capital
        if total_cost > self.capital:
            self.flash_message(f"Insufficient capital! Need ${self._format_number(total_cost, 0)}", 13)
            return
            
        # Validate vessel utilization
        if quantity < freight_quote.capacity * 0.9:
            self.flash_message("Insufficient inventory for full vessel!", 13)
            return
        
        # Execute trade
        self.capital -= total_cost
        fob_quote.inventory -= quantity  # Deduct from inventory
        
        trade = Trade(
            commodity=self.selected_commodity,
            origin=self.selected_origin,
            destination=self.selected_destination,
            quantity=quantity,
            fob_price=fob_quote.offer,
            freight_rate=freight_quote.rate,
            vessel_type=self.selected_vessel,
            execution_week=self.market.current_week,
            execution_year=self.market.year,
            status=TradeStatus.SAILING,
            fob_cost=fob_cost,
            freight_cost=freight_cost,
            total_cost=total_cost
        )
        
        self._check_tender_fulfillment(trade)
        self.active_trades.append(trade)
        self.flash_message(
            f"Executed {self._format_number(quantity/1000, 0)}k MT {self.selected_commodity} at ${self._format_number(fob_quote.offer, 2)}", 
            4
        )

    def _check_tender_fulfillment(self, trade):
        """Check if trade matches any outstanding tender obligations"""
        # Look for matching awarded tenders
        for tender_id, tender in self.tender_manager.historical_tenders.items():
            if tender.status != TenderStatus.AWARDED:
                continue
                
            # Get player's awards for this tender
            player_offers = [
                offer for offer in self.tender_manager.offers.get(tender_id, [])
                if (offer.participant == "PLAYER" and 
                    offer.status in [OfferStatus.ACCEPTED, OfferStatus.PARTIALLY_ACCEPTED] and
                    offer.origin == trade.origin)
            ]
            
            for offer in player_offers:
                # Check if trade matches tender requirements
                if (trade.commodity == tender.commodity and
                    trade.destination == tender.buyer and
                    trade.quantity <= offer.awarded_quantity - tender.delivered_quantity):
                    
                    # Record delivery
                    self.tender_deliveries.append(
                        TenderDelivery(
                            tender_id=tender_id,
                            offer_id=offer.id,
                            quantity=trade.quantity,
                            delivered=True,
                            delivery_week=self.market.current_week,
                            delivery_year=self.market.year
                        )
                    )
                    
                    # Update delivered quantity
                    tender.delivered_quantity += trade.quantity
                    
                    self.flash_message(
                        f"Trade fulfills tender obligation to {tender.buyer}",
                        4
                    )
                    return
                
    def handle_storage_request(self, location: str, commodity: str):
        """Handle storage with proper costs and inventory management"""
        if location not in self.storage_manager.facilities:
            self.flash_message(f"No storage facility at {location}!", 13)
            return

        facility = self.storage_manager.facilities[location]  # Get the facility object
        
        # Get current market quote
        market_key = (commodity, location)
        if market_key not in self.market.fob_markets:
            self.flash_message("No market quote available!", 13)
            return

        quote = self.market.fob_markets[market_key]
        standard_lot = 5000  # 5,000 MT standard storage lot

        # Check available inventory
        if quote.inventory < standard_lot:
            self.flash_message(f"Insufficient inventory at {location}!", 13)
            return

        # Calculate total costs including purchase
        purchase_cost = quote.offer * standard_lot
        handling_cost = facility.handling_cost * standard_lot  # Use facility object
        total_cost = purchase_cost + handling_cost

        if total_cost > self.capital:
            self.flash_message("Insufficient capital!", 13)
            return

        # Execute storage
        success, cost = self.storage_manager.store_grain(location, commodity, standard_lot)
        if success:
            self.capital -= total_cost
            quote.inventory -= standard_lot  # Reduce available inventory
            
            self.storage_positions.append(
                StorageTransaction(
                    facility=location,
                    commodity=commodity,
                    quantity=standard_lot,
                    entry_date=self.market.current_week,
                    entry_price=quote.offer,
                    handling_cost_paid=handling_cost
                )
            )
            self.flash_message(
                f"Bought and stored {self._format_number(standard_lot/1000, 0)}K MT {commodity}",
                4
            )
        else:
            self.flash_message("Failed to store grain!", 13)

    def handle_storage_costs(self):
        """Handle the player-facing aspects of storage costs"""
        costs = self.storage_manager.update_storage_costs(self.market.current_week)
        total_cost = sum(costs.values())
        
        if total_cost > 0:
            if total_cost > self.capital:
                self.flash_message("WARNING: Insufficient funds for storage costs!", 13)
                self._handle_forced_liquidation()
            else:
                self.capital -= total_cost
                for pos in self.storage_positions:
                    pos.storage_cost_paid += costs.get(pos.facility, 0)
                self.flash_message(f"Monthly storage costs: ${self._format_number(total_cost, 0)}", 6)

    def _handle_forced_liquidation(self):
        """Handle forced liquidation of storage positions when unable to pay costs"""
        for pos in self.storage_positions[:]:  # Use slice copy to allow modification during iteration
            # Attempt to sell at market price (with penalty)
            market_quote = self.market.fob_markets.get((pos.commodity, pos.facility))
            if market_quote:
                liquidation_price = market_quote.bid * 0.95  # 5% penalty
                revenue = liquidation_price * pos.quantity
                self.capital += revenue
                
                # Remove from storage
                success, cost = self.storage_manager.remove_grain(pos.facility, pos.commodity, pos.quantity)
                if success:
                    self.storage_positions.remove(pos)
                    self.flash_message(
                        f"FORCED LIQUIDATION: Sold {self._format_number(pos.quantity/1000, 0)}k MT {pos.commodity} at ${self._format_number(liquidation_price, 2)}", 
                        13
                    )

    def get_selected_storage_position(self):
        """Get currently selected storage position"""
        if not self.storage_positions:
            return None
        if 0 <= self.selected_storage_row < len(self.storage_positions):
            return self.storage_positions[self.selected_storage_row]
        return None


    def execute_storage_action(self, action_type: str):
        """Execute storage-related actions: sell from storage or ship to destination"""
        self.selected_destination = list(self.market.destinations.keys())[self.selected_destination_idx]
    
        position = self.get_selected_storage_position()
        if not position:
            self.flash_message("No storage position selected!", 13)
            return
            
        # Check for market price at storage location
        market_quote = self.market.fob_markets.get((position.commodity, position.facility))
        if not market_quote:
            self.flash_message("No market price available!", 13)
            return

        if action_type == "SELL":
            self._sell_from_storage(position, market_quote)
        elif action_type == "TRANSPORT":
            self._transport_from_storage(position)

    def _sell_from_storage(self, position: StorageTransaction, market_quote: MarketQuote):
        """Sell commodity from storage"""
        # Calculate sale proceeds
        sale_price = market_quote.bid
        revenue = sale_price * position.quantity
        
        # Get facility handling cost
        facility = self.storage_manager.facilities[position.facility]
        handling_cost = facility.handling_cost * position.quantity
        
        # Calculate profit/loss
        total_costs = (position.entry_price * position.quantity) + position.storage_cost_paid + handling_cost
        profit = revenue - total_costs - handling_cost
        
        # Remove from storage
        success, _ = self.storage_manager.remove_grain(position.facility, 
                                                    position.commodity, 
                                                    position.quantity)
        if success:
            self.capital += revenue - handling_cost  # Deduct handling cost now
            self.storage_positions.remove(position)
            
            roi = (profit / total_costs) * 100 if total_costs > 0 else 0
            self.flash_message(
                f"Sold {self._format_number(position.quantity/1000, 0)}k MT {position.commodity} " +
                f"ROI: {self._format_number(roi, 1)}% (${self._format_number(profit, 0)})",
                4 if profit > 0 else 3
            )
        else:
            self.flash_message("Failed to sell from storage!", 13)

    def _transport_from_storage(self, position: StorageTransaction):
        """Transport commodity from storage to destination with proper vessel utilization"""
        # First, combine all positions of the same commodity at this location
        total_quantity = sum(
            pos.quantity for pos in self.storage_positions
            if pos.facility == position.facility and pos.commodity == position.commodity
        )
        
        # Calculate volume weighted average price for combined positions
        total_value = sum(
            pos.quantity * pos.entry_price for pos in self.storage_positions
            if pos.facility == position.facility and pos.commodity == position.commodity
        )
        vwap = total_value / total_quantity if total_quantity > 0 else 0

        # Get all relevant positions
        relevant_positions = [
            pos for pos in self.storage_positions
            if pos.facility == position.facility and pos.commodity == position.commodity
        ]

        # Get freight quote and check vessel constraints
        freight_quotes = self.market.freight_markets.get((position.facility, self.selected_destination))
        if not freight_quotes or self.selected_vessel not in freight_quotes:
            self.flash_message("Invalid freight route!", 13)
            return
            
        freight_quote = freight_quotes[self.selected_vessel]
        vessel_capacity = VesselType.__dict__[self.selected_vessel]["capacity"]
        
        if total_quantity < vessel_capacity * 0.5:
            self.flash_message(
                f"Need at least {self._format_number(vessel_capacity * 0.5/1000, 0)}K MT for {self.selected_vessel} " +
                f"(have {self._format_number(total_quantity/1000, 0)}K MT)", 
                13
            )
            return
        
        # Calculate quantity based on vessel capacity
        quantity = min(total_quantity, vessel_capacity)
        utilization = (quantity / vessel_capacity) * 100
        utilization_penalty = 0
        
        if utilization < 90:
            base_freight_rate = freight_quote.rate
            utilization_penalty = (90 - utilization) / 100
            adjusted_rate = base_freight_rate * (1 + utilization_penalty)
            
            cost_increase = ((adjusted_rate - base_freight_rate) / base_freight_rate) * 100
            warning = (f"Warning: Vessel only {utilization:.1f}% utilized. " +
                    f"Freight cost increases by {cost_increase:.1f}% " +
                    f"(${self._format_number(base_freight_rate, 2)}/MT → " +
                    f"${self._format_number(adjusted_rate, 2)}/MT)")
            
            self.flash_message(warning, 6)
            for _ in range(30):
                pyxel.flip()
        
        # Calculate costs
        freight_cost = freight_quote.rate * quantity * (1 + utilization_penalty)
        handling_cost = (self.storage_manager.facilities[position.facility].handling_cost +
                        self.storage_manager.facilities[self.selected_destination].handling_cost) * quantity
        total_cost = freight_cost + handling_cost
        
        if total_cost > self.capital:
            self.flash_message(f"Insufficient capital! Need ${self._format_number(total_cost, 0)}", 13)
            return
        
        # Remove quantity from positions
        remaining_to_remove = quantity
        positions_to_remove = []
        
        for pos in relevant_positions:
            if remaining_to_remove <= 0:
                break
                
            amount_from_position = min(pos.quantity, remaining_to_remove)
            success, _ = self.storage_manager.remove_grain(pos.facility, pos.commodity, amount_from_position)
            
            if success:
                remaining_to_remove -= amount_from_position
                if amount_from_position == pos.quantity:
                    positions_to_remove.append(pos)
                else:
                    pos.quantity -= amount_from_position
            else:
                self.flash_message("Failed to remove from storage!", 13)
                return
        
        if remaining_to_remove > 0:
            self.flash_message("Error: Could not remove all quantity!", 13)
            return
            
        # Remove the positions we fully used
        for pos in positions_to_remove:
            self.storage_positions.remove(pos)
        
        # Create the transport trade
        trade = Trade(
            commodity=position.commodity,
            origin=position.facility,
            destination=self.selected_destination,
            quantity=quantity,
            fob_price=vwap,
            freight_rate=freight_quote.rate * (1 + utilization_penalty),
            vessel_type=self.selected_vessel,
            execution_week=self.market.current_week,
            execution_year=self.market.year,
            status=TradeStatus.SAILING,
            fob_cost=vwap * quantity,
            freight_cost=freight_cost,
            total_cost=total_cost
        )
        
        self.capital -= total_cost
        self.active_trades.append(trade)
        
        self.flash_message(
            f"Started transport of {self._format_number(quantity/1000, 0)}k MT {position.commodity} " +
            f"via {self.selected_vessel} to {self.selected_destination}",
            4
        )

    def get_market_cfr(self, tender: TenderAnnouncement, origin: str) -> float:
        """Calculate market CFR based on FOB and freight for the specific vessel type"""
        fob = self.market.fob_markets.get((tender.commodity, origin))
        if not fob:
            return None
            
        freight = self.market.freight_markets.get((origin, tender.buyer))
        if not freight or tender.required_vessel_type not in freight:
            return None
            
        return fob.offer + freight[tender.required_vessel_type].rate

    def draw_panel(self, x: int, y: int, w: int, h: int, title: str = ""):
        """Draw a panel with optional title"""
        pyxel.rect(x, y, w, h, 1)
        pyxel.rectb(x, y, w, h, 2)
        
        if title:
            title_width = len(title) * 4 + 4
            pyxel.rect(x+2, y, title_width, 7, 1)
            pyxel.text(x+4, y+1, title, 7)
            pyxel.line(x+2, y+7, x+2+title_width, y+7, 2)

    def draw_scrollbar(self, x: int, y: int, h: int, total_items: int, visible_items: int):
        """Draw a scrollbar for lists"""
        if total_items <= visible_items:
            return
            
        pyxel.rect(x, y, 3, h, 1)
        handle_height = max(20, h * (visible_items / total_items))
        handle_pos = y + (h - handle_height) * (self.scroll_offset / (total_items - visible_items))
        pyxel.rect(x, handle_pos, 3, handle_height, 2)

    def draw_market_view(self):
        """Draw the market overview screen with improved selection visibility"""
        # Draw selection info panel at top
        self.draw_panel(5, 30, 440, 25, "CURRENT SELECTION")
        selection_y = 44  # Adjusted y position
        dest_list = list(self.market.destinations.keys())
        vessel_list = self.vessel_types
        
        # Draw selection info
        pyxel.text(10, selection_y, f"SELECTED: {self.selected_commodity} FROM {self.selected_origin}", 7)
        pyxel.text(200, selection_y, f"TO: {dest_list[self.selected_destination_idx]}", 7)
        pyxel.text(350, selection_y, f"VESSEL: {vessel_list[self.selected_vessel_idx]}", 7)

        # Market Overview Panel - Origins only
        self.draw_panel(5, 60, 440, 210, "MARKET OVERVIEW")
        
        # Draw column headers
        headers = ["COMMODITY", "PORT", "BID", "OFFER", "6M LOW", "6M HIGH", "STOCK KT"]
        x_positions = [10, 90, 170, 220, 270, 320, 370]

        y = 70
        for header, x in zip(headers, x_positions):
            pyxel.text(x, y, header, 8)
        
        # Filter for origin markets only
        origin_markets = {
            key: quote for key, quote in self.market.fob_markets.items()
            if key[1] in self.market.origins
        }
        
        # Get market status for crop cycle info
        market_status = self.market.get_market_status()
        
        # Draw market data for origins
        y = 78
        visible_rows = (210 - 20) // 8

        for i, ((commodity, port), quote) in enumerate(list(origin_markets.items())[self.scroll_offset:]):
            if i >= visible_rows:
                break
                
            # Alternating row backgrounds
            row_bg_color = 2 if i % 2 == 0 else 1
            pyxel.rect(7, y-1, 436, 8, row_bg_color)
            
            # Highlight selected row with brighter color
            if i + self.scroll_offset == self.selected_row:
                pyxel.rect(7, y-1, 436, 8, 5)  # Use lighter blue for selection
            
            # Inside the market data drawing loop:
            price_color = quote.price_direction()
            pyxel.text(10, y, f"{commodity[:8]}", 7)
            pyxel.text(90, y, f"{port[:10]}", 7)

            if quote.has_valid_inventory():
                pyxel.text(170, y, self._format_number(quote.bid, 2), price_color)
                pyxel.text(220, y, self._format_number(quote.offer, 2), price_color)
            else:
                pyxel.text(170, y, " - ", 3)
                pyxel.text(220, y, " - ", 3)

            # Use orange (color 6) for new highs/lows
            low_color = 6 if quote.new_low_this_week else 3
            high_color = 6 if quote.new_high_this_week else 4

            pyxel.text(270, y, self._format_number(quote.six_month_low, 2), low_color)
            pyxel.text(320, y, self._format_number(quote.six_month_high, 2), high_color)
            
            # Add crop cycle information
            if (commodity, port) in market_status["crop_cycles"]:
                cycle_info = market_status["crop_cycles"][(commodity, port)]
                stock_pct = cycle_info["stock_percentage"]
                
                # Convert percentage to actual KT value based on base production
                region = self.market.port_to_region.get(port)
                if region:
                    cycle = self.market.crop_cycles_manager.cycles.get((region, commodity))
                    if cycle:
                        stock_kt = int((cycle.current_stocks / 1000))  # Convert MT to KT
                        stock_color = (4 if stock_kt > 500 else 
                                    6 if stock_kt > 200 else 
                                    3 if stock_kt < 100 else 7)
                        stock_text = f"{stock_kt}"
                        pyxel.text(370, y, stock_text, stock_color)
            
            y += 8
            
        # Draw scrollbar for origins
        self.draw_scrollbar(445, 95, 160, len(origin_markets), visible_rows)
        
        # Destination Markets Panel
        self.draw_panel(5, 275, 440, 160, "DESTINATION MARKETS")
        
        # Draw destination market headers
        dest_headers = ["DESTINATION", "BID", "OFFER", "PAYMENT", "RISK"]
        dest_x = [10, 120, 170, 220, 270]
        y = 288
        for header, x in zip(dest_headers, dest_x):
            pyxel.text(x, y, header, 8)
        y += 12

        # Show destination market prices
        for i, (dest_name, dest_port) in enumerate(self.market.destinations.items()):
            # Alternating row backgrounds
            row_bg_color = 2 if i % 2 == 0 else 1
            pyxel.rect(7, y-1, 436, 8, row_bg_color)
            
            # Highlight selected destination with blue
            is_selected = dest_name == dest_list[self.selected_destination_idx]
            if is_selected:
                pyxel.rect(7, y-1, 436, 8, 5)  # Use blue highlight
            
            # Get destination price quote
            dest_quote = self.market.get_destination_price(
                self.selected_commodity, 
                self.selected_origin,
                dest_name
            )
            
            if dest_quote:
                # Format payment terms and colors
                payment_days = dest_port.payment_delay_days
                payment_text = f"{payment_days}d" if payment_days < 100 else f"{payment_days//30}m"
                risk_color = 4 if dest_port.risk_level <= 2 else 6 if dest_port.risk_level == 3 else 3
                text_color = 7  # Always use white for destination name
                
                pyxel.text(10, y, f"{dest_name[:15]}", text_color)
                pyxel.text(120, y, self._format_number(dest_quote["bid"], 2), dest_quote["price_direction"])
                pyxel.text(170, y, self._format_number(dest_quote["offer"], 2), dest_quote["price_direction"])
                pyxel.text(220, y, payment_text, 7)
                pyxel.text(270, y, str(dest_port.risk_level), risk_color)
                
                condition = self.market.local_market_conditions[dest_name]
                condition_color = 4 if condition > 1.05 else 3 if condition < 0.95 else 7
                condition_text = "▲" if condition > 1.05 else "▼" if condition < 0.95 else "-"
                pyxel.text(310, y, condition_text, condition_color)
            
            y += 10

    # Update the draw_freight_view method in the Game class
    def draw_freight_view(self):
        """Draw improved freight rates view with origin selection"""
        self.draw_panel(5, 30, 440, 380, "FREIGHT RATES")
        
        # Draw origin selection bar
        y = 45
        pyxel.text(10, y, "SELECT ORIGIN:", 8)
        
        # Draw origins in a horizontal list
        origin_x = 90
        origins = list(self.market.origins.keys())
        for origin in origins:
            is_selected = origin == self.selected_freight_origin
            color = 10 if is_selected else 7  # Highlight selected origin
            pyxel.text(origin_x, y, origin, color)
            origin_x += len(origin) * 4 + 10  # Space between origins
        
        # Draw rates table headers
        y += 20
        pyxel.text(10, y, "DESTINATION", 8)
        pyxel.text(120, y, "HANDY", 8)
        pyxel.text(200, y, "SUPRA", 8)
        pyxel.text(280, y, "PMAX", 8)
        pyxel.text(360, y, "STATUS", 8)
        
        y += 15
        
        # Show freight rates only for selected origin
        for dest in self.market.destinations.keys():
            route_key = (self.selected_freight_origin, dest)
            if route_key in self.market.freight_markets:
                vessels = self.market.freight_markets[route_key]
                
                # Calculate delays
                origin_port = self.market.origins.get(self.selected_freight_origin)
                dest_port = self.market.destinations.get(dest)
                total_delay = 0
                if origin_port and dest_port:
                    total_delay = origin_port.get_total_delay() + dest_port.get_total_delay()
                
                # Draw destination
                pyxel.text(10, y, dest[:15], 7)
                
                # Draw rates for each vessel type with proper formatting
                if "HANDYMAX" in vessels:
                    rate = vessels["HANDYMAX"].rate
                    last_rate = vessels["HANDYMAX"].last_rate
                    rate_color = 4 if rate < last_rate else 3 if rate > last_rate else 7
                    pyxel.text(120, y, f"${self._format_number(rate, 2)}", rate_color)
                    
                if "SUPRAMAX" in vessels:
                    rate = vessels["SUPRAMAX"].rate
                    last_rate = vessels["SUPRAMAX"].last_rate
                    rate_color = 4 if rate < last_rate else 3 if rate > last_rate else 7
                    pyxel.text(200, y, f"${self._format_number(rate, 2)}", rate_color)
                    
                if "PANAMAX" in vessels:
                    rate = vessels["PANAMAX"].rate
                    last_rate = vessels["PANAMAX"].last_rate
                    rate_color = 4 if rate < last_rate else 3 if rate > last_rate else 7
                    pyxel.text(280, y, f"${self._format_number(rate, 2)}", rate_color)
                
                # Draw status with proper number formatting
                if total_delay == 0:
                    status_text = "Normal"
                    status_color = 4
                else:
                    # Format the delay with only 1 decimal place
                    status_text = f"+{self._format_number(total_delay, 1)}d"
                    status_color = 6 if total_delay < 7 else 3
                    
                pyxel.text(360, y, status_text, status_color)
                y += 10
    
    def draw_trades_view(self):
        """Draw active and completed trades view"""
        # Active Trades Panel
        self.draw_panel(5, 30, 440, 180, "ACTIVE TRADES")
        
        y = 45
        headers = ["COMMODITY", "ROUTE", "PRICE", "SIZE", "STATUS", "ETA", "PAYMENT"]
        x_pos = [10, 60, 160, 220, 280, 340, 380]
        
        # Draw headers
        for header, x in zip(headers, x_pos):
            pyxel.text(x, y, header, 8)
        y += 12

        # Draw active trades
        for trade in self.active_trades:
            status_color = 6 if trade.status == TradeStatus.SAILING else 4
            pyxel.text(10, y, f"{trade.commodity[:8]}", 7)
            pyxel.text(60, y, f"{trade.origin[:6]}->{trade.destination[:6]}", 8)
            pyxel.text(160, y, f"${self._format_number(trade.fob_price, 2)}", 7)
            pyxel.text(220, y, self._format_number(trade.quantity/1000, 0) + "k", 8)
            pyxel.text(280, y, trade.status.value, status_color)
            
            # Calculate and show ETA
            if trade.status == TradeStatus.SAILING:
                eta_weeks = trade.execution_week + math.ceil(trade.freight_rate / 7)
                if eta_weeks > 52:
                    eta_weeks -= 52
                pyxel.text(340, y, f"W{eta_weeks}", 6)
            
            # Calculate and show payment date
            if trade.status in [TradeStatus.SAILING, TradeStatus.DELIVERED]:
                dest_port = self.market.destinations[trade.destination]
                payment_weeks = math.ceil(dest_port.payment_delay_days / 7)
                if trade.arrival_week:
                    payment_week = trade.arrival_week + payment_weeks
                    payment_year = trade.arrival_year
                    if payment_week > 52:
                        payment_week -= 52
                        payment_year += 1
                    pyxel.text(380, y, f"W{payment_week}/{payment_year}", 8)
                else:
                    eta_payment = eta_weeks + payment_weeks
                    if eta_payment > 52:
                        eta_payment -= 52
                    pyxel.text(380, y, f"~W{eta_payment}", 6)
            y += 10

        # Completed Trades Panel
        self.draw_panel(5, 220, 440, 180, "COMPLETED TRADES")
        y = 235
        
        headers = ["COMMODITY", "ROUTE", "P&L", "ROI", "DAYS"]
        x_pos = [10, 60, 160, 250, 320]
        
        # Draw headers
        for header, x in zip(headers, x_pos):
            pyxel.text(x, y, header, 8)
        y += 12

        # Draw completed trades (latest first)
        for trade in reversed(self.completed_trades[-12:]):
            profit_color = 4 if trade.estimated_profit > 0 else 3
            roi = (trade.estimated_profit / trade.total_cost * 100) if trade.total_cost > 0 else 0
            
            pyxel.text(10, y, f"{trade.commodity[:8]}", 7)
            pyxel.text(60, y, f"{trade.origin[:6]}->{trade.destination[:6]}", 8)
            pyxel.text(160, y, f"${self._format_number(trade.estimated_profit, 0)}", profit_color)
            pyxel.text(250, y, f"{self._format_number(roi, 1)}%", profit_color)
            
            # Calculate duration
            duration = ((trade.arrival_week + (trade.arrival_year * 52)) - 
                       (trade.execution_week + (trade.execution_year * 52))) * 7
            pyxel.text(320, y, f"{duration}d", 8)
            y += 10

    def draw_storage_view(self):
        """Draw storage view with improved layout and VWAP calculations"""
        # Draw selection info panel at top - kept small for more space
        self.draw_panel(5, 30, 440, 30, "CURRENT SELECTION")
        selection_y = 40
        dest_list = list(self.market.destinations.keys())
        vessel_list = self.vessel_types
        
        # Draw basic selection info compactly
        pyxel.text(10, selection_y, f"Selected: {self.selected_storage_facility} | " +
                f"Ship To: {dest_list[self.selected_destination_idx]} | " +
                f"Vessel: {vessel_list[self.selected_vessel_idx]}", 10)
        
        # Draw Facilities Panel - now taller to use more space
        self.draw_panel(5, 65, 440, 180, "STORAGE FACILITIES")  # Increased height from 150 to 180
        y = 80
        
        # Draw facility headers
        headers = ["FACILITY", "MONTHLY COST", "HANDLING", "CAPACITY", "UTIL%"]
        x_pos = [10, 150, 250, 320, 390]
        for header, x in zip(headers, x_pos):
            pyxel.text(x, y, header, 8)
        y += 15

        # Calculate visible rows and total rows for facilities
        visible_rows_facilities = (180 - 30) // 10  # Adjusted for new panel height
        facilities_list = list(self.storage_manager.facilities.items())
        total_rows_facilities = len(facilities_list)

        # Draw facilities with scrolling
        for i, (location, facility) in enumerate(facilities_list[self.scroll_offset:self.scroll_offset + visible_rows_facilities]):
            status = self.storage_manager.get_facility_status(location)
            if not status:
                continue
            
            # Highlight selected facility
            is_selected = location == self.selected_storage_facility
            if is_selected:
                pyxel.rect(7, y-1, 436, 8, 2)
            
            text_color = 10 if is_selected else 7
            utilization = (facility.total_capacity - facility.available_capacity) / facility.total_capacity
            utilization_color = 4 if utilization < 0.8 else 6 if utilization < 0.9 else 3
            
            pyxel.text(x_pos[0], y, f"{status['name']}", text_color)
            pyxel.text(x_pos[1], y, f"${self._format_number(status['monthly_cost'], 2)}/MT", 7)
            pyxel.text(x_pos[2], y, f"${self._format_number(status['handling_cost'], 2)}/MT", 7)
            pyxel.text(x_pos[3], y, f"{self._format_number(status['total_capacity']/1000, 0)}k", 7)
            pyxel.text(x_pos[4], y, f"{self._format_number(utilization*100, 1)}%", utilization_color)
            y += 10

        # Draw scrollbar for facilities
        if total_rows_facilities > visible_rows_facilities:
            self.draw_scrollbar(445, 95, 135, total_rows_facilities, visible_rows_facilities)  # Adjusted height
            
        # Storage Positions Panel - moved closer to facilities panel
        self.draw_panel(5, 250, 440, 190, "YOUR STORAGE POSITIONS")  # Adjusted y position and height
        y = 265
        
        if not self.storage_positions:
            pyxel.text(170, y+50, "NO COMMODITIES IN STORAGE", 3)
        else:
            # Calculate VWAP and MTM for each unique location/commodity pair
            position_summary = {}
            for pos in self.storage_positions:
                key = (pos.facility, pos.commodity)
                if key not in position_summary:
                    position_summary[key] = {
                        "total_quantity": 0,
                        "total_value": 0,
                        "storage_cost": 0
                    }
                summary = position_summary[key]
                summary["total_quantity"] += pos.quantity
                summary["total_value"] += pos.quantity * pos.entry_price
                summary["storage_cost"] += pos.storage_cost_paid
            
            # Draw headers
            headers = ["LOCATION", "COMMODITY", "QUANTITY", "VWAP", "MTM", "COST/MT"]
            x_pos = [10, 100, 190, 280, 350, 400]
            for header, x in zip(headers, x_pos):
                pyxel.text(x, y, header, 8)
            y += 12

            # Calculate visible rows for positions
            visible_rows_positions = (190 - 40) // 10  # Adjusted for panel height
            position_items = list(position_summary.items())
            total_rows_positions = len(position_items)

            # Draw summarized positions with scrolling
            for i, ((facility, commodity), summary) in enumerate(position_items[self.storage_scroll_offset:self.storage_scroll_offset + visible_rows_positions]):
                vwap = summary["total_value"] / summary["total_quantity"]
                storage_per_mt = summary["storage_cost"] / summary["total_quantity"]
                
                # Get current market price
                market_quote = self.market.fob_markets.get((commodity, facility))
                mtm_color = 7
                mtm_text = "N/A"
                
                if market_quote:
                    mtm = market_quote.bid - vwap
                    mtm_color = 4 if mtm > 0 else 3
                    mtm_text = f"${self._format_number(mtm, 2)}"
                
                pyxel.text(x_pos[0], y, f"{facility[:12]}", 7)
                pyxel.text(x_pos[1], y, f"{commodity}", 7)
                pyxel.text(x_pos[2], y, f"{self._format_number(summary['total_quantity']/1000, 0)}k", 7)
                pyxel.text(x_pos[3], y, f"${self._format_number(vwap, 2)}", 7)
                pyxel.text(x_pos[4], y, mtm_text, mtm_color)
                pyxel.text(x_pos[5], y, f"${self._format_number(storage_per_mt, 2)}", 6)
                y += 10

            # Draw scrollbar for positions
            if total_rows_positions > visible_rows_positions:
                self.draw_scrollbar(445, 280, 145, total_rows_positions, visible_rows_positions)

    def draw_analysis_view(self):
        """Draw market analysis and statistics with complete P&L breakdown"""
        self.draw_panel(5, 30, 440, 380, "MARKET ANALYSIS")
        
        # Performance metrics
        y = 45
        # Calculate trading P&L
        trading_profit = sum(t.estimated_profit for t in self.completed_trades)
        
        # Calculate tender penalties
        # Calculate tender costs
        tender_costs = self.tender_penalties  # Penalties from failed deliveries
        tender_costs += sum(
            tender.participation_cost
            for tender_id, tender in self.tender_manager.historical_tenders.items()
            if any(offer.participant == "PLAYER" 
                for offer in self.tender_manager.offers.get(tender_id, []))
        )
        
        # Calculate storage costs
        storage_costs = sum(pos.storage_cost_paid + pos.handling_cost_paid 
                        for pos in self.storage_positions)
        
        # Calculate total P&L
        total_profit = self.capital - self.initial_capital
        roi = (total_profit / self.initial_capital * 100) if self.initial_capital > 0 else 0
        
        # Display P&L breakdown
        pyxel.text(10, y, "P&L BREAKDOWN", 7)
        y += 15
        
        pyxel.text(20, y, f"Trading P&L: ${self._format_number(trading_profit, 0)}", 
                4 if trading_profit > 0 else 3)
        y += 10
        pyxel.text(20, y, f"Tender Costs: ${self._format_number(tender_costs, 0)}", 6)
        y += 10
        pyxel.text(20, y, f"Storage Costs: ${self._format_number(storage_costs, 0)}", 6)
        y += 10
        pyxel.text(20, y, f"Total P&L: ${self._format_number(total_profit, 0)}", 
                4 if total_profit > 0 else 3)
        y += 10
        pyxel.text(20, y, f"ROI: {self._format_number(roi, 1)}%", 
                4 if roi > 0 else 3)
        y += 20

        # Storage Analysis
        if self.storage_positions:
            pyxel.text(10, y, "STORAGE ANALYSIS", 7)
            y += 15
            
            total_stored = sum(pos.quantity for pos in self.storage_positions)
            total_cost = sum(pos.storage_cost_paid for pos in self.storage_positions)
            avg_cost = total_cost / total_stored if total_stored > 0 else 0
            
            pyxel.text(20, y, f"Total Stored: {self._format_number(total_stored/1000, 0)}k MT", 8)
            y += 10
            pyxel.text(20, y, f"Storage Costs: ${self._format_number(total_cost, 0)}", 6)
            y += 10
            pyxel.text(20, y, f"Avg Cost/MT: ${self._format_number(avg_cost, 2)}", 8)
            y += 20

        # Port Analysis
        pyxel.text(10, y, "PORT STATUS", 7)
        y += 15
        
        for name, port in self.market.origins.items():
            risk_color = 4 if port.risk_level < 3 else 6 if port.risk_level < 4 else 3
            delay_color = 4 if port.get_total_delay() < 2 else 6 if port.get_total_delay() < 4 else 3
            
            pyxel.text(20, y, f"{name[:10]:<10}", 7)
            pyxel.text(90, y, f"Risk: {port.risk_level}", risk_color)
            pyxel.text(160, y, f"Delay: {self._format_number(port.get_total_delay(), 0)}d", delay_color)
            y += 10


    def draw_tender_view(self):
        """Draw tender view showing active tenders and offer options"""
        # Draw active tenders panel
        self.draw_panel(5, 30, 440, 180, "ACTIVE TENDERS")
        
        y = 45
        headers = ["BUYER", "COMMODITY", "QUANTITY", "ORIGINS", "WINDOW", "DEADLINE"]
        x_pos = [10, 75, 150, 230, 320, 380]
        
        # Draw headers
        for header, x in zip(headers, x_pos):
            pyxel.text(x, y, header, 8)
        y += 12
        
        # Draw active tenders
        active_tenders = list(self.tender_manager.active_tenders.values())
        if not active_tenders:
            pyxel.text(170, 105, "NO ACTIVE TENDERS AVAILABLE", 3)
        else:
            for i, tender in enumerate(active_tenders):
                # Highlight selected tender
                if i == self.selected_tender_idx:
                    pyxel.rect(7, y-1, 436, 8, 2)
                
                pyxel.text(10, y, f"{tender.buyer[:8]}", 7)
                pyxel.text(75, y, f"{tender.commodity}", 7)
                pyxel.text(150, y, f"{self._format_number(tender.total_quantity/1000, 0)}K MT", 7)
                origins_text = "/".join(o[:3] for o in tender.permitted_origins)
                pyxel.text(200, y, f"{origins_text}", 7)
                pyxel.text(320, y, f"W{tender.shipment_start}-{tender.shipment_end}", 7)
                pyxel.text(380, y, f"W{tender.submission_deadline}", 6)
                y += 10
        
        # Always draw offer submission panel
        self.draw_panel(5, 220, 215, 180, "SUBMIT OFFER")
        
        if not active_tenders:
            # Show message when no active tenders
            pyxel.text(55, 275, "NO ACTIVE TENDERS AVAILABLE", 3)
        elif 0 <= self.selected_tender_idx < len(active_tenders):
            selected_tender = active_tenders[self.selected_tender_idx]
            y = 235
            # Condensed version of existing submit offer display
            pyxel.text(10, y, f"Selected: {selected_tender.buyer[:8]}", 10)
            y += 15
            pyxel.text(10, y, f"Origin: {self.current_tender_offer['origin']}", 7)
            y += 10
            vessels_text = f"Vessels: {self.current_tender_offer['num_vessels']} x {self._format_number(selected_tender.min_cargo_size/1000, 0)}K"
            pyxel.text(10, y, vessels_text, 7)
            y += 10
            price_text = f"CFR: ${self._format_number(self.current_tender_offer['price'], 2)}"
            pyxel.text(10, y, price_text, 7)
            
            # Submit button
            pyxel.rect(10, y+30, 100, 12, 2)
            pyxel.text(15, y+32, "SUBMIT OFFER", 7)
        
        # Always draw the right panel - Player's Active Awards
        self.draw_panel(225, 220, 220, 180, "YOUR ACTIVE AWARDS")
        
        # Get all player's active awarded tenders
        player_awards = []
        for tender_id, tender in self.tender_manager.historical_tenders.items():
            if tender.status == TenderStatus.AWARDED:
                player_offers = [
                    offer for offer in self.tender_manager.offers.get(tender_id, [])
                    if (offer.participant == "PLAYER" and 
                        offer.status in [OfferStatus.ACCEPTED, OfferStatus.PARTIALLY_ACCEPTED])
                ]
                if player_offers:
                    for offer in player_offers:
                        remaining_qty = offer.awarded_quantity - tender.delivered_quantity
                        if remaining_qty > 0:
                            player_awards.append({
                                'tender': tender,
                                'offer': offer,
                                'remaining': remaining_qty
                            })
        
        y = 235
        headers = ["BUYER", "ORIGIN", "GRAIN", "WINDOW", "REMAIN"]
        x_pos = [230, 276, 322, 366, 400]
        for header, x in zip(headers, x_pos):
            pyxel.text(x, y, header, 8)
        y += 12
        
        if not player_awards:
            pyxel.text(302, 275, "NO ACTIVE AWARDS", 3)
        else:
            # Draw awards
            for award in player_awards:
                tender = award['tender']
                offer = award['offer']
                pyxel.text(230, y, tender.buyer[:6], 7)
                pyxel.text(276, y, offer.origin[:6], 7)
                pyxel.text(322, y, tender.commodity[:6], 7)
                pyxel.text(366, y, f"W{tender.shipment_start}-{tender.shipment_end}", 7)
                pyxel.text(400, y, f"{self._format_number(award['remaining']/1000, 0)}K", 7)
                y += 10
                # Show price on next line
                pyxel.text(230, y, f"${self._format_number(offer.price, 2)}/MT", 8)
                y += 12
    
    def draw_tender_results(self):
        """Draw popup showing tender results"""
        if not self.show_tender_results or not self.current_tender_result:
            return
                
        # Unpack the current result
        tender_id, awards = self.current_tender_result
        
        # Calculate centered position for the popup window
        window_width = 300
        window_height = 320
        x = (450 - window_width) // 2
        y = (450 - window_height) // 2
        
        # Draw window background and border
        pyxel.rect(x, y, window_width, window_height, 1)
        pyxel.rectb(x, y, window_width, window_height, 2)
        
        # Get tender details - IMPORTANT: Use correct tender ID
        tender = self.tender_manager.historical_tenders.get(tender_id)
        
        if not tender:
            return
                
        # Draw title bar
        title = f"TENDER RESULTS - {tender.buyer}"
        title_x = x + (window_width - len(title) * 4) // 2
        pyxel.rect(x, y, window_width, 10, 2)
        pyxel.text(title_x, y + 2, title, 7)
        
        # Draw tender info
        content_y = y + 20
        pyxel.text(x + 10, content_y, f"COMMODITY: {tender.commodity}", 7)
        content_y += 10
        quantity_text = f"TOTAL QUANTITY: {self._format_number(tender.total_quantity/1000, 0)}K MT"
        pyxel.text(x + 10, content_y, quantity_text, 7)
        content_y += 20
        
        # Draw awards section
        if awards:
            pyxel.text(x + 10, content_y, "AWARDS:", 8)
            content_y += 15
            
            # Group awards by participant
            awards_by_participant = {}
            for offer in awards:
                if offer.participant not in awards_by_participant:
                    awards_by_participant[offer.participant] = []
                awards_by_participant[offer.participant].append(offer)
            
            # Sort participants for consistent display
            sorted_participants = sorted(awards_by_participant.keys())
            for participant in sorted_participants:
                offers = awards_by_participant[participant]
                pyxel.text(x + 20, content_y, f"{participant}:", 7)
                content_y += 10
                
                for offer in offers:
                    # Get the pricing analysis
                    analysis = self.tender_manager.analyze_tender_pricing(tender, offer)
                    
                    # Display the offer details
                    qty_text = f"{self._format_number(offer.awarded_quantity/1000, 0)}K MT"
                    price_text = f"${self._format_number(offer.price, 2)}"
                    result_text = f"{qty_text} at {price_text} from {offer.origin}"
                    
                    status_color = 4 if offer.status == OfferStatus.ACCEPTED else (
                        6 if offer.status == OfferStatus.PARTIALLY_ACCEPTED else 3)
                    
                    pyxel.text(x + 30, content_y, result_text, status_color)
                    content_y += 10
                    
                    # Add margin analysis if available
                    if analysis:
                        margin_text = f"Margin: {analysis['implied_margin']:.1f}% (Cost: ${self._format_number(analysis['total_cost'], 2)}/MT)"
                        margin_color = 4 if analysis["implied_margin"] > 0 else 3
                        pyxel.text(x + 40, content_y, margin_text, margin_color)
                        content_y += 10
        else:
            pyxel.text(x + 10, content_y, "No awards made - tender cancelled", 8)
        
        # Draw navigation/close instructions
        if self.pending_tender_results:
            count_text = f"({len(self.pending_tender_results)} more results)"
            count_x = x + (window_width - len(count_text) * 4) // 2
            pyxel.text(count_x, y + window_height - 30, count_text, 6)
        
        exit_text = "PRESS X TO CLOSE"
        exit_x = x + (window_width - len(exit_text) * 4) // 2
        exit_color = 7 if (pyxel.frame_count // 15) % 2 == 0 else 5
        pyxel.text(exit_x, y + window_height - 15, exit_text, exit_color)
        
    def draw_status_bar(self):
        """Draw top status bar"""
        pyxel.rect(0, 0, 450, 20, 1)
        
        # Draw capital with color based on performance
        capital_color = 4 if self.capital > self.initial_capital else 3
        profit_loss = self.capital - self.initial_capital
        pl_text = f"+${self._format_number(profit_loss, 0)}" if profit_loss >= 0 else f"-${self._format_number(abs(profit_loss), 0)}"
        
        pyxel.text(10, 6, f"CAPITAL: ${self._format_number(self.capital, 0)} ({pl_text})", capital_color)
        pyxel.text(200, 6, f"Week {self.market.current_week:02d}/{self.market.year}", 7)
        
        # Draw storage costs if any positions exist
        if self.storage_positions:
            total_storage_cost = sum(pos.storage_cost_paid for pos in self.storage_positions)
            pyxel.text(300, 6, f"Storage: ${self._format_number(total_storage_cost, 0)}", 6)

    def draw_navigation_tabs(self):
        """Draw navigation tabs"""
        tab_width = 56  # Adjusted for 7 tabs
        tabs = ['MARKET', 'FREIGHT', 'FUTURES', 'TRADES', 'STORAGE', 'TENDERS', 'ANALYSIS']
        
        for i, tab in enumerate(tabs):
            x = i * tab_width
            selected = self.view_mode == tab
            pyxel.rect(x, 20, tab_width-1, 10, 2 if selected else 1)
            pyxel.text(x+5, 22, tab, 7 if selected else 8)
            
    def draw_flash_messages(self):
        """Draw flash messages with fade effect"""
        current_frame = pyxel.frame_count
        y = 410
        
        for msg, color, frame in self.flash_messages:
            age = current_frame - frame
            if age < 90:  # 3 seconds
                alpha = 1.0 - (age / 90)
                display_color = color if alpha > 0.5 else 8
                pyxel.text(10, y, msg, display_color)
                y -= 10

    def flash_message(self, msg: str, color: int = 7):
        """Add a flash message to the queue"""
        self.flash_messages.append((msg, color, pyxel.frame_count))
        if len(self.flash_messages) > 5:
            self.flash_messages.pop(0)
    
    def submit_tender_offer(self):
        """Submit current tender offer with participation cost and validation"""
        if not self.tender_manager.active_tenders:
            return
            
        tender = list(self.tender_manager.active_tenders.values())[self.selected_tender_idx]
        
        # Check if player is blacklisted
        if "PLAYER" in tender.blacklisted_participants:
            self.flash_message("You are currently blacklisted from participating in this buyer's tenders!", 13)
            return
        
        # Check if player can afford participation cost
        if self.capital < tender.participation_cost:
            self.flash_message(f"Insufficient funds for tender participation cost (${tender.participation_cost:,})", 13)
            return
            
        # Validate offer
        if not self.current_tender_offer['origin'] or self.current_tender_offer['price'] <= 0:
            self.flash_message("Invalid offer! Check origin and price.", 13)
            return
            
        # Validate vessel size matches requirement
        vessel_capacity = VesselType.__dict__[tender.required_vessel_type]["capacity"]
        total_quantity = vessel_capacity * self.current_tender_offer['num_vessels']
        if total_quantity > tender.total_quantity:
            self.flash_message(f"Offer quantity exceeds tender requirement!", 13)
            return
        
        # Deduct participation cost
        self.capital -= tender.participation_cost
        
        # Create and submit offer
        offer = TenderOffer(
            tender_id=tender.id,
            participant="PLAYER",
            origin=self.current_tender_offer['origin'],
            quantity=total_quantity,
            num_vessels=self.current_tender_offer['num_vessels'],
            price=self.current_tender_offer['price'],
            submission_week=self.market.current_week
        )
        
        if self.tender_manager.submit_offer(tender.id, offer):
            self.flash_message(
                f"Offer submitted: {offer.quantity/1000:.0f}K MT at ${offer.price:.2f}", 4)
            # Reset offer
            self.current_tender_offer = {'num_vessels': 1, 'origin': None, 'price': 0.0}
        else:
            self.flash_message("Failed to submit offer!", 13)

    def check_tender_deliveries(self):
        """Check for undelivered tender cargoes and apply penalties only after delivery window"""
        current_week = self.market.current_week
        current_year = self.market.year
        current_total_weeks = current_week + (current_year * 52)
        
        for tender_id, tender in list(self.tender_manager.historical_tenders.items()):
            if tender.status != TenderStatus.AWARDED:
                continue
                
            # Get player's offers for this tender
            player_offers = [
                offer for offer in self.tender_manager.offers.get(tender_id, [])
                if (offer.participant == "PLAYER" and 
                    offer.status in [OfferStatus.ACCEPTED, OfferStatus.PARTIALLY_ACCEPTED])
            ]
            
            if not player_offers:
                continue
            
            # Calculate tender end week in absolute weeks
            tender_year = tender.announcement_date // 52
            tender_end_total_weeks = tender.shipment_end + (tender_year * 52)
            
            # Only check tenders where the delivery window has fully passed
            # Add a grace period of 1 week after window ends
            if current_total_weeks > tender_end_total_weeks + 1:
                for offer in player_offers:
                    # Check if penalty already applied
                    if hasattr(offer, 'penalty_applied'):
                        continue
                        
                    # Calculate remaining undelivered quantity
                    remaining_quantity = offer.awarded_quantity - tender.delivered_quantity
                    
                    if remaining_quantity > 0:
                        # Apply penalty once
                        penalty = self.TENDER_DEFAULT_PENALTY
                        self.capital -= penalty
                        self.tender_penalties += penalty
                        offer.penalty_applied = True
                        
                        # Blacklist player
                        self.tender_manager.blacklist_participant(
                            "PLAYER",
                            tender.buyer,
                            current_total_weeks + 52  # Blacklist for one year
                        )
                        
                        self.flash_message(
                            f"PENALTY: ${self._format_number(penalty, 0)} for failing to deliver {self._format_number(remaining_quantity/1000, 0)}K MT to {tender.buyer}!",
                            13
                        )
                        self.flash_message(
                            f"WARNING: Blacklisted from {tender.buyer}'s tenders for one year!",
                            13
                        )

    def _update_tender_selection(self):
        """Update tender selection to ensure it's valid"""
        active_tenders = list(self.tender_manager.active_tenders.values())
        
        if not active_tenders:  # If no active tenders
            self.selected_tender_idx = 0
            self.current_tender_offer = {'num_vessels': 1, 'origin': None, 'price': 0.0}
            return
        
        # Ensure selected index is within bounds
        if self.selected_tender_idx >= len(active_tenders):
            self.selected_tender_idx = max(0, len(active_tenders) - 1)
            self.current_tender_offer = {'num_vessels': 1, 'origin': None, 'price': 0.0}

    def _update_tender_offer_price(self, tender, origin):
        """Update tender offer price based on market CFR for the selected origin"""
        # Get market CFR for the origin
        market_cfr = self.get_market_cfr(tender, origin)
        if market_cfr:
            # Set the initial price to market CFR
            self.current_tender_offer['price'] = round(market_cfr, 2)
            return True
        return False
    
    def show_next_tender_result(self):
        """Show next tender result from queue"""
        if self.tender_results_queue:
            self.current_tender_result = self.tender_results_queue.pop(0)
            tender_id, awards = self.current_tender_result

            self.show_tender_results = True
        else:
            self.current_tender_result = None
            self.show_tender_results = False

   

    def update(self):
        """Handle game updates and input"""
        # First, handle trade recap updates if visible
        self.trade_recap.update()
        self.price_graph.update()

        # Only process other inputs if trade recap is not showing
        if not self.trade_recap.visible:
            # Global controls
            if pyxel.btnp(pyxel.KEY_Q):
                pyxel.quit()

            # View navigation with TAB
            if pyxel.btnp(pyxel.KEY_TAB):
                self.view_mode = {
                    'MARKET': 'FREIGHT',
                    'FREIGHT': 'FUTURES',
                    'FUTURES': 'TRADES',
                    'TRADES': 'STORAGE',
                    'STORAGE': 'TENDERS',  # Changed from 'ANALYSIS'
                    'TENDERS': 'ANALYSIS', # Added new transition
                    'ANALYSIS': 'MARKET'
                }[self.view_mode]
                self.selected_row = 0
                
            # Advance game time
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.market.update_markets()
                self.check_tender_deliveries()
                self.update_trades()
                self.handle_storage_costs()
                
                # Get tender results in a cleaner format
                tender_results = self.tender_manager.update_tenders(self.market.current_week)
                if tender_results:
                    self.tender_results_queue = tender_results
                    # Show first result immediately
                    self.current_tender_result = self.tender_results_queue.pop(0)
                    self.show_tender_results = True
                    self.pending_tender_results = self.tender_results_queue.copy()
                    
            # Update handling of tender result navigation
            if self.show_tender_results:
                if pyxel.btnp(pyxel.KEY_X):
                    if self.pending_tender_results:
                        self.current_tender_result = self.pending_tender_results.pop(0)
                    else:
                        self.show_tender_results = False
                        self.current_tender_result = None
            
            # Handle view-specific controls
            if self.view_mode == 'MARKET':
                # Market view controls
                if pyxel.btnp(pyxel.KEY_B):  # Buy to storage
                    if self.selected_row < len(self.market.fob_markets):
                        commodity, origin = list(self.market.fob_markets.keys())[self.selected_row]
                        self.handle_storage_request(origin, commodity)
                elif pyxel.btnp(pyxel.KEY_RETURN):  # Execute trade
                    self.execute_trade()
                elif pyxel.btnp(pyxel.KEY_UP):  # Move selection up
                    self.selected_row = max(0, self.selected_row - 1)
                    self._update_selection()
                elif pyxel.btnp(pyxel.KEY_DOWN):  # Move selection down
                    self.selected_row = min(len(self.market.fob_markets) - 1, self.selected_row + 1)
                    self._update_selection()
                elif pyxel.btnp(pyxel.KEY_G):
                    keys = list(self.market.fob_markets.keys())
                    if 0 <= self.selected_row < len(keys):
                        commodity, port = keys[self.selected_row]
                        market_data = self.market.fob_markets[(commodity, port)]
                        if not self.price_graph.show(market_data, commodity, port):
                            self.flash_message("Not enough price history available yet!", 6)

            elif self.view_mode == 'FREIGHT':
                # Handle origin selection with left/right arrows
                if pyxel.btnp(pyxel.KEY_LEFT):
                    origins = list(self.market.origins.keys())
                    current_idx = origins.index(self.selected_freight_origin)
                    self.selected_freight_origin = origins[(current_idx - 1) % len(origins)]
                elif pyxel.btnp(pyxel.KEY_RIGHT):
                    origins = list(self.market.origins.keys())
                    current_idx = origins.index(self.selected_freight_origin)
                    self.selected_freight_origin = origins[(current_idx + 1) % len(origins)]

            elif self.view_mode == 'STORAGE':
                # Storage facility scrolling with up/down
                if pyxel.btnp(pyxel.KEY_UP) or pyxel.btnp(pyxel.KEY_DOWN):
                    facilities_list = list(self.storage_manager.facilities.items())
                    total_rows = len(facilities_list)
                    visible_rows = (180 - 30) // 10  # Match the visible rows calculation from draw method
                    
                    if pyxel.btnp(pyxel.KEY_DOWN):
                        # First try to move selection within visible area
                        if self.selected_row < min(total_rows - 1, self.scroll_offset + visible_rows - 1):
                            self.selected_row += 1
                        # If at bottom of visible area, scroll down
                        elif self.scroll_offset < total_rows - visible_rows:
                            self.scroll_offset += 1
                            self.selected_row += 1
                    else:  # UP key
                        if self.selected_row > self.scroll_offset:
                            self.selected_row -= 1
                        elif self.scroll_offset > 0:
                            self.scroll_offset -= 1
                            self.selected_row -= 1
                    
                    # Update selected facility based on current row
                    if 0 <= self.selected_row < total_rows:
                        self.selected_storage_facility = facilities_list[self.selected_row][0]
                
                # Storage positions scrolling with +/- keys
                if pyxel.btnp(pyxel.KEY_MINUS) or pyxel.btnp(pyxel.KEY_PLUS):
                    position_items = list({(pos.facility, pos.commodity) 
                                        for pos in self.storage_positions})
                    visible_rows_positions = (190 - 40) // 10
                    max_scroll = max(0, len(position_items) - visible_rows_positions)
                    
                    if pyxel.btnp(pyxel.KEY_PLUS):
                        self.storage_scroll_offset = min(self.storage_scroll_offset + 1, max_scroll)
                    else:
                        self.storage_scroll_offset = max(0, self.storage_scroll_offset - 1)
                
                # Destination selection with left/right
                if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_RIGHT):
                    dest_list = list(self.market.destinations.keys())
                    if pyxel.btnp(pyxel.KEY_RIGHT):
                        self.selected_destination_idx = (self.selected_destination_idx + 1) % len(dest_list)
                    else:
                        self.selected_destination_idx = (self.selected_destination_idx - 1) % len(dest_list)
                    self.selected_destination = dest_list[self.selected_destination_idx]
                
                # Storage actions
                if len(self.storage_positions) > 0:
                    if pyxel.btnp(pyxel.KEY_S):
                        self.execute_storage_action("SELL")
                    elif pyxel.btnp(pyxel.KEY_T):
                        self.execute_storage_action("TRANSPORT")

                # Vessel type selection
                if pyxel.btnp(pyxel.KEY_V):
                    self.selected_vessel_idx = (self.selected_vessel_idx + 1) % len(self.vessel_types)
                    self.selected_vessel = self.vessel_types[self.selected_vessel_idx]

            elif self.view_mode == 'FUTURES':
                self.futures_ui.handle_input()
                self.futures_manager.update_positions()

            elif self.view_mode == 'TENDERS':
                active_tenders = list(self.tender_manager.active_tenders.values())
                self._update_tender_selection()
                
                if len(active_tenders) > 0:
                    current_tender = active_tenders[self.selected_tender_idx]
                    
                    if pyxel.btnp(pyxel.KEY_O):  # Cycle origins
                        if not self.current_tender_offer['origin']:
                            new_origin = current_tender.permitted_origins[0]
                        else:
                            try:
                                idx = current_tender.permitted_origins.index(self.current_tender_offer['origin'])
                                new_origin = current_tender.permitted_origins[
                                    (idx + 1) % len(current_tender.permitted_origins)]
                            except ValueError:
                                new_origin = current_tender.permitted_origins[0]
                        
                        self.current_tender_offer['origin'] = new_origin
                        self._update_tender_offer_price(current_tender, new_origin)
                    
                    elif pyxel.btnp(pyxel.KEY_V):  # Change number of vessels
                        tender = active_tenders[self.selected_tender_idx]
                        max_vessels = min(
                            tender.max_vessels,
                            tender.total_quantity // VesselType.__dict__[tender.required_vessel_type]["capacity"]
                        )
                        self.current_tender_offer['num_vessels'] = (
                            (self.current_tender_offer['num_vessels'] % max_vessels) + 1)
                    
                    elif pyxel.btnp(pyxel.KEY_LEFT):  # Decrease price
                        self.current_tender_offer['price'] = max(0, 
                            self.current_tender_offer['price'] - 0.25)
                    
                    elif pyxel.btnp(pyxel.KEY_RIGHT):  # Increase price
                        self.current_tender_offer['price'] += 0.25
                    
                    elif pyxel.btnp(pyxel.KEY_RETURN):  # Submit offer
                        self.submit_tender_offer()
                    
                    if pyxel.btnp(pyxel.KEY_UP):
                        self.selected_tender_idx = (self.selected_tender_idx - 1) % len(active_tenders)
                        # Reset offer when selecting different tender
                        self.current_tender_offer = {'num_vessels': 1, 'origin': None, 'price': 0.0}
                    elif pyxel.btnp(pyxel.KEY_DOWN):
                        self.selected_tender_idx = (self.selected_tender_idx + 1) % len(active_tenders)
                        # Reset offer when selecting different tender
                        self.current_tender_offer = {'num_vessels': 1, 'origin': None, 'price': 0.0}
                        
                    current_tender = active_tenders[self.selected_tender_idx]
            
            # Destination and vessel selection (shared between Market and Storage views)
            if self.view_mode in ['MARKET', 'STORAGE']:
                dest_list = list(self.market.destinations.keys())
                
                if pyxel.btnp(pyxel.KEY_RIGHT):
                    # Only update destination if not already handling facility selection
                    if self.view_mode != 'STORAGE' or not (pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_RIGHT)):
                        self.selected_destination_idx = (self.selected_destination_idx + 1) % len(dest_list)
                        self.selected_destination = dest_list[self.selected_destination_idx]
                elif pyxel.btnp(pyxel.KEY_LEFT):
                    # Only update destination if not already handling facility selection
                    if self.view_mode != 'STORAGE' or not (pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_RIGHT)):
                        self.selected_destination_idx = (self.selected_destination_idx - 1) % len(dest_list)
                        self.selected_destination = dest_list[self.selected_destination_idx]
                elif pyxel.btnp(pyxel.KEY_V):  # Cycle vessel type
                    self.selected_vessel_idx = (self.selected_vessel_idx + 1) % len(self.vessel_types)
                    self.selected_vessel = self.vessel_types[self.selected_vessel_idx]
            
            # Handle scrolling for any view that needs it
            self._handle_scrolling()
    

    def draw(self):
        """Main draw function"""
        pyxel.cls(0)
        
        self.draw_status_bar()
        self.draw_navigation_tabs()
        
        if self.view_mode == 'MARKET':
            self.draw_market_view()
        elif self.view_mode == 'FREIGHT':
            self.draw_freight_view()
        elif self.view_mode == 'TRADES':
            self.draw_trades_view()
        elif self.view_mode == 'STORAGE':
            self.draw_storage_view()
        elif self.view_mode == 'TENDERS':
            self.draw_tender_view()
        elif self.view_mode == 'FUTURES':
            self.futures_ui.draw()
        elif self.view_mode == 'ANALYSIS':
            self.draw_analysis_view()
        
        # Draw contextual help text based on view
        pyxel.rect(0, 440, 450, 10, 1)
        if self.view_mode == 'MARKET':
            help_text = "SPACE: Next Week  TAB: View  ^/v: Select  </>: Route  V: Vessel  G: Graph  RETURN: Trade  B: Buy to Silo"
        elif self.view_mode == 'STORAGE':
            help_text = "SPACE: Next Week  TAB: View  ^/v: Facilities  +/-: Positions  </>: Routes  V: Vessel  S: Sell  T: Transport"
        elif self.view_mode == 'FUTURES':
            help_text = "SPACE: Next Week  TAB: View  F: Asset Class  ^/v: Select  </>: Quantity  X: Lot Size  B/S: Buy/Sell"
        elif self.view_mode == 'TENDERS':
            help_text = "SPACE: Next Week  TAB: View  ^/v: Select Tender  O: Origin  V: Vessels  </>: Price  RETURN: Submit"
        else:
            help_text = "SPACE: Next Week  TAB: View  ^/v: Select  </>: Route"
        pyxel.text(10, 442, help_text, 8)

        self.trade_recap.draw()
        self.price_graph.draw()

        if self.show_tender_results:
            self.draw_tender_results()
        
        self.draw_flash_messages()
   

if __name__ == "__main__":
    Game()
    
