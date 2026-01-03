/**
 * OrderBook.h - High-Performance Limit Order Book
 * 
 * Institutional-Grade Price-Time Priority Matching Engine
 * Designed for microsecond latency and >10M msgs/sec throughput
 * 
 * Architecture: C++20 with STL containers optimized for LOB operations
 * Thread Safety: Single-threaded design (external synchronization required)
 */

#ifndef INSTITUTIONAL_ENGINE_ORDERBOOK_H
#define INSTITUTIONAL_ENGINE_ORDERBOOK_H

#include "Order.h"

#include <map>
#include <deque>
#include <unordered_map>
#include <vector>
#include <optional>
#include <functional>
#include <string>

namespace institutional {

/**
 * OrderBook - Limit Order Book with Price-Time Priority Matching
 * 
 * Key Features:
 * - Strict Price-Time Priority (FIFO at each price level)
 * - Automatic Crossed Book Resolution (instant matching)
 * - O(log N) insertion, O(1) best bid/ask lookup
 * - Trade event callbacks for downstream processing
 * 
 * Memory Model:
 * - std::map for price levels (ordered tree, cache-friendly iteration)
 * - std::deque for order queues (efficient front/back operations)
 * - std::unordered_map for O(1) order lookup by ID
 */
class OrderBook {
public:
    // Type aliases for clarity
    using OrderQueue = std::deque<LimitOrder>;
    using BidBook = std::map<double, OrderQueue, std::greater<double>>; // Descending
    using AskBook = std::map<double, OrderQueue, std::less<double>>;    // Ascending
    using OrderIndex = std::unordered_map<uint64_t, std::pair<double, Side>>;
    using TradeCallback = std::function<void(const Trade&)>;
    
    /**
     * Constructor
     * @param symbol Trading symbol (e.g., "SPY")
     */
    explicit OrderBook(const std::string& symbol = "DEFAULT");
    
    /**
     * Destructor
     */
    ~OrderBook() = default;
    
    // Non-copyable, movable
    OrderBook(const OrderBook&) = delete;
    OrderBook& operator=(const OrderBook&) = delete;
    OrderBook(OrderBook&&) = default;
    OrderBook& operator=(OrderBook&&) = default;
    
    // ========================================================================
    // CORE OPERATIONS
    // ========================================================================
    
    /**
     * Add a new order to the book
     * 
     * CRITICAL BEHAVIOR:
     * - If order crosses the spread, it will be matched immediately
     * - Remaining quantity (if any) is added to the book
     * - Returns the order ID (same as input) or 0 if rejected
     * 
     * @param id Unique order identifier
     * @param price Limit price
     * @param quantity Order quantity
     * @param is_buy true for BID, false for ASK
     * @return Order ID if accepted, 0 if rejected
     */
    uint64_t add_order(uint64_t id, double price, double quantity, bool is_buy);
    
    /**
     * Cancel an existing order
     * 
     * @param id Order ID to cancel
     * @return true if order was found and cancelled, false otherwise
     */
    bool cancel_order(uint64_t id);
    
    /**
     * Modify an existing order (cancel + replace)
     * 
     * NOTE: Loses time priority at the price level
     * 
     * @param id Order ID to modify
     * @param new_price New limit price
     * @param new_quantity New quantity
     * @return true if modification successful
     */
    bool modify_order(uint64_t id, double new_price, double new_quantity);
    
    // ========================================================================
    // MARKET DATA
    // ========================================================================
    
    /**
     * Get best bid price
     * @return Best bid price, or std::nullopt if no bids
     */
    [[nodiscard]] std::optional<double> get_best_bid() const;
    
    /**
     * Get best ask price
     * @return Best ask price, or std::nullopt if no asks
     */
    [[nodiscard]] std::optional<double> get_best_ask() const;
    
    /**
     * Get best bid quantity
     * @return Total quantity at best bid
     */
    [[nodiscard]] double get_best_bid_qty() const;
    
    /**
     * Get best ask quantity
     * @return Total quantity at best ask
     */
    [[nodiscard]] double get_best_ask_qty() const;
    
    /**
     * Get bid-ask spread
     * @return Spread (ask - bid), or -1 if book is empty
     */
    [[nodiscard]] double get_spread() const;
    
    /**
     * Get mid price
     * @return (best_bid + best_ask) / 2, or -1 if book is empty
     */
    [[nodiscard]] double get_mid_price() const;
    
    /**
     * Get order book snapshot (top N levels)
     * @param levels Number of price levels to include (default 5)
     * @return BookSnapshot structure
     */
    [[nodiscard]] BookSnapshot get_snapshot(size_t levels = 5) const;
    
    /**
     * Get snapshot as JSON string (for Python/visualization)
     * @param levels Number of price levels
     * @return JSON-formatted string
     */
    [[nodiscard]] std::string get_snapshot_json(size_t levels = 5) const;
    
    // ========================================================================
    // STATISTICS
    // ========================================================================
    
    /**
     * Get total number of active orders
     */
    [[nodiscard]] size_t get_order_count() const;
    
    /**
     * Get number of bid levels
     */
    [[nodiscard]] size_t get_bid_level_count() const;
    
    /**
     * Get number of ask levels
     */
    [[nodiscard]] size_t get_ask_level_count() const;
    
    /**
     * Get total volume on bid side
     */
    [[nodiscard]] double get_total_bid_volume() const;
    
    /**
     * Get total volume on ask side
     */
    [[nodiscard]] double get_total_ask_volume() const;
    
    /**
     * Get trade count
     */
    [[nodiscard]] uint64_t get_trade_count() const { return trade_count_; }
    
    /**
     * Get total traded volume
     */
    [[nodiscard]] double get_traded_volume() const { return traded_volume_; }
    
    /**
     * Get symbol
     */
    [[nodiscard]] const std::string& get_symbol() const { return symbol_; }
    
    // ========================================================================
    // CALLBACKS
    // ========================================================================
    
    /**
     * Set callback for trade events
     */
    void set_trade_callback(TradeCallback callback);
    
    /**
     * Clear the entire order book
     */
    void clear();
    
    /**
     * Get recent trades
     * @param count Number of recent trades to return
     */
    [[nodiscard]] std::vector<Trade> get_recent_trades(size_t count = 10) const;

private:
    // ========================================================================
    // PRIVATE METHODS
    // ========================================================================
    
    /**
     * Match an incoming order against the opposite side
     * @param order The incoming order (may be modified)
     * @return Remaining quantity after matching
     */
    double match_order(LimitOrder& order);
    
    /**
     * Add order to the appropriate book side
     */
    void insert_order(const LimitOrder& order);
    
    /**
     * Remove order from index
     */
    void remove_from_index(uint64_t id);
    
    /**
     * Execute a trade between two orders
     */
    void execute_trade(LimitOrder& aggressive, LimitOrder& passive, double qty);
    
    /**
     * Clean empty price levels
     */
    void cleanup_empty_levels();
    
    // ========================================================================
    // DATA MEMBERS
    // ========================================================================
    
    std::string symbol_;           // Trading symbol
    BidBook bids_;                 // Bid side (descending by price)
    AskBook asks_;                 // Ask side (ascending by price)
    OrderIndex order_index_;       // O(1) order lookup
    
    uint64_t next_trade_id_;       // Trade ID counter
    uint64_t trade_count_;         // Total trades executed
    double traded_volume_;         // Total volume traded
    
    std::vector<Trade> recent_trades_; // Ring buffer for recent trades
    static constexpr size_t MAX_RECENT_TRADES = 1000;
    
    TradeCallback trade_callback_; // Optional trade callback
};

} // namespace institutional

#endif // INSTITUTIONAL_ENGINE_ORDERBOOK_H





