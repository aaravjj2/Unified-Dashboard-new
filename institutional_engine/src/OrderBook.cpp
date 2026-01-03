/**
 * OrderBook.cpp - High-Performance Limit Order Book Implementation
 * 
 * Institutional-Grade Price-Time Priority Matching Engine
 * 
 * CRITICAL INVARIANTS:
 * 1. Best Bid < Best Ask (no crossed book state persists)
 * 2. Orders at same price are matched in FIFO order (time priority)
 * 3. Aggressive orders match immediately before resting
 */

#include "OrderBook.h"

#include <sstream>
#include <iomanip>
#include <algorithm>
#include <cmath>

namespace institutional {

// ============================================================================
// CONSTRUCTOR
// ============================================================================

OrderBook::OrderBook(const std::string& symbol)
    : symbol_(symbol)
    , bids_()
    , asks_()
    , order_index_()
    , next_trade_id_(1)
    , trade_count_(0)
    , traded_volume_(0.0)
    , recent_trades_()
    , trade_callback_(nullptr)
{
    recent_trades_.reserve(MAX_RECENT_TRADES);
}

// ============================================================================
// CORE OPERATIONS
// ============================================================================

uint64_t OrderBook::add_order(uint64_t id, double price, double quantity, bool is_buy) {
    // Validate inputs
    if (!validate_order(price, quantity)) {
        return 0;  // Rejected
    }
    
    // Check for duplicate ID
    if (order_index_.find(id) != order_index_.end()) {
        return 0;  // Duplicate ID rejected
    }
    
    // Create the order
    Side side = is_buy ? Side::BID : Side::ASK;
    LimitOrder order(id, price, quantity, side, get_timestamp_ns());
    
    // **CRITICAL**: Check for crossed book and match immediately
    double remaining = match_order(order);
    
    // If order is fully filled, don't add to book
    if (remaining <= 0.0) {
        return id;  // Fully filled
    }
    
    // Update order quantity to remaining amount
    order.quantity = remaining;
    order.filled_qty = 0.0;
    
    // Insert remaining quantity into the book
    insert_order(order);
    
    return id;
}

bool OrderBook::cancel_order(uint64_t id) {
    // Find the order in the index
    auto it = order_index_.find(id);
    if (it == order_index_.end()) {
        return false;  // Order not found
    }
    
    double price = it->second.first;
    Side side = it->second.second;
    
    // Remove from the appropriate book
    if (side == Side::BID) {
        auto level_it = bids_.find(price);
        if (level_it != bids_.end()) {
            auto& queue = level_it->second;
            queue.erase(
                std::remove_if(queue.begin(), queue.end(),
                    [id](const LimitOrder& o) { return o.id == id; }),
                queue.end()
            );
            // Clean up empty level
            if (queue.empty()) {
                bids_.erase(level_it);
            }
        }
    } else {
        auto level_it = asks_.find(price);
        if (level_it != asks_.end()) {
            auto& queue = level_it->second;
            queue.erase(
                std::remove_if(queue.begin(), queue.end(),
                    [id](const LimitOrder& o) { return o.id == id; }),
                queue.end()
            );
            // Clean up empty level
            if (queue.empty()) {
                asks_.erase(level_it);
            }
        }
    }
    
    // Remove from index
    order_index_.erase(it);
    
    return true;
}

bool OrderBook::modify_order(uint64_t id, double new_price, double new_quantity) {
    // Cancel the existing order
    auto it = order_index_.find(id);
    if (it == order_index_.end()) {
        return false;
    }
    
    Side side = it->second.second;
    
    // Cancel and re-add (loses time priority)
    if (!cancel_order(id)) {
        return false;
    }
    
    // Re-add with new parameters
    return add_order(id, new_price, new_quantity, side == Side::BID) != 0;
}

// ============================================================================
// MATCHING ENGINE
// ============================================================================

double OrderBook::match_order(LimitOrder& order) {
    double remaining = order.quantity;
    
    if (order.side == Side::BID) {
        // BUY order: match against ASK side
        // Match if buy price >= best ask (crossed book)
        while (remaining > 0.0 && !asks_.empty()) {
            auto& [best_ask_price, ask_queue] = *asks_.begin();
            
            // Check if we can match (buy price must be >= ask price)
            if (order.price < best_ask_price) {
                break;  // No more matching possible
            }
            
            // Match against orders at this price level (FIFO)
            while (remaining > 0.0 && !ask_queue.empty()) {
                LimitOrder& passive = ask_queue.front();
                
                // Determine fill quantity
                double fill_qty = std::min(remaining, passive.remaining_qty());
                
                // Execute the trade
                execute_trade(order, passive, fill_qty);
                
                // Update quantities
                remaining -= fill_qty;
                passive.filled_qty += fill_qty;
                
                // Remove filled passive orders
                if (passive.is_filled()) {
                    remove_from_index(passive.id);
                    ask_queue.pop_front();
                }
            }
            
            // Clean up empty price level
            if (ask_queue.empty()) {
                asks_.erase(asks_.begin());
            }
        }
    } else {
        // SELL order: match against BID side
        // Match if sell price <= best bid (crossed book)
        while (remaining > 0.0 && !bids_.empty()) {
            auto& [best_bid_price, bid_queue] = *bids_.begin();
            
            // Check if we can match (sell price must be <= bid price)
            if (order.price > best_bid_price) {
                break;  // No more matching possible
            }
            
            // Match against orders at this price level (FIFO)
            while (remaining > 0.0 && !bid_queue.empty()) {
                LimitOrder& passive = bid_queue.front();
                
                // Determine fill quantity
                double fill_qty = std::min(remaining, passive.remaining_qty());
                
                // Execute the trade
                execute_trade(order, passive, fill_qty);
                
                // Update quantities
                remaining -= fill_qty;
                passive.filled_qty += fill_qty;
                
                // Remove filled passive orders
                if (passive.is_filled()) {
                    remove_from_index(passive.id);
                    bid_queue.pop_front();
                }
            }
            
            // Clean up empty price level
            if (bid_queue.empty()) {
                bids_.erase(bids_.begin());
            }
        }
    }
    
    return remaining;
}

void OrderBook::execute_trade(LimitOrder& aggressive, LimitOrder& passive, double qty) {
    // Determine execution price (always passive order's price)
    double exec_price = passive.price;
    
    // Create trade record
    Trade trade;
    trade.trade_id = next_trade_id_++;
    trade.price = exec_price;
    trade.quantity = qty;
    trade.timestamp = get_timestamp_ns();
    
    // Assign buy/sell order IDs
    if (aggressive.side == Side::BID) {
        trade.buy_order_id = aggressive.id;
        trade.sell_order_id = passive.id;
    } else {
        trade.buy_order_id = passive.id;
        trade.sell_order_id = aggressive.id;
    }
    
    // Update statistics
    trade_count_++;
    traded_volume_ += qty;
    
    // Store in recent trades (ring buffer behavior)
    if (recent_trades_.size() >= MAX_RECENT_TRADES) {
        recent_trades_.erase(recent_trades_.begin());
    }
    recent_trades_.push_back(trade);
    
    // Invoke callback if set
    if (trade_callback_) {
        trade_callback_(trade);
    }
}

void OrderBook::insert_order(const LimitOrder& order) {
    if (order.side == Side::BID) {
        bids_[order.price].push_back(order);
    } else {
        asks_[order.price].push_back(order);
    }
    
    // Add to index
    order_index_[order.id] = {order.price, order.side};
}

void OrderBook::remove_from_index(uint64_t id) {
    order_index_.erase(id);
}

// ============================================================================
// MARKET DATA
// ============================================================================

std::optional<double> OrderBook::get_best_bid() const {
    if (bids_.empty()) {
        return std::nullopt;
    }
    return bids_.begin()->first;
}

std::optional<double> OrderBook::get_best_ask() const {
    if (asks_.empty()) {
        return std::nullopt;
    }
    return asks_.begin()->first;
}

double OrderBook::get_best_bid_qty() const {
    if (bids_.empty()) {
        return 0.0;
    }
    double total = 0.0;
    for (const auto& order : bids_.begin()->second) {
        total += order.remaining_qty();
    }
    return total;
}

double OrderBook::get_best_ask_qty() const {
    if (asks_.empty()) {
        return 0.0;
    }
    double total = 0.0;
    for (const auto& order : asks_.begin()->second) {
        total += order.remaining_qty();
    }
    return total;
}

double OrderBook::get_spread() const {
    auto bid = get_best_bid();
    auto ask = get_best_ask();
    
    if (!bid || !ask) {
        return -1.0;
    }
    
    return *ask - *bid;
}

double OrderBook::get_mid_price() const {
    auto bid = get_best_bid();
    auto ask = get_best_ask();
    
    if (!bid || !ask) {
        return -1.0;
    }
    
    return (*bid + *ask) / 2.0;
}

BookSnapshot OrderBook::get_snapshot(size_t levels) const {
    BookSnapshot snapshot;
    snapshot.timestamp = get_timestamp_ns();
    
    levels = std::min(levels, BookSnapshot::MAX_LEVELS);
    
    // Collect bid levels
    size_t bid_count = 0;
    for (const auto& [price, queue] : bids_) {
        if (bid_count >= levels) break;
        
        double total_qty = 0.0;
        for (const auto& order : queue) {
            total_qty += order.remaining_qty();
        }
        
        snapshot.bids[bid_count] = PriceLevel(price, total_qty, 
                                               static_cast<uint32_t>(queue.size()));
        bid_count++;
    }
    snapshot.bid_levels = bid_count;
    
    // Collect ask levels
    size_t ask_count = 0;
    for (const auto& [price, queue] : asks_) {
        if (ask_count >= levels) break;
        
        double total_qty = 0.0;
        for (const auto& order : queue) {
            total_qty += order.remaining_qty();
        }
        
        snapshot.asks[ask_count] = PriceLevel(price, total_qty,
                                               static_cast<uint32_t>(queue.size()));
        ask_count++;
    }
    snapshot.ask_levels = ask_count;
    
    return snapshot;
}

std::string OrderBook::get_snapshot_json(size_t levels) const {
    auto snapshot = get_snapshot(levels);
    
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(2);
    
    oss << "{\n";
    oss << "  \"symbol\": \"" << symbol_ << "\",\n";
    oss << "  \"timestamp\": " << snapshot.timestamp << ",\n";
    
    // Best Bid/Ask
    auto bb = get_best_bid();
    auto ba = get_best_ask();
    oss << "  \"best_bid\": " << (bb ? *bb : 0.0) << ",\n";
    oss << "  \"best_ask\": " << (ba ? *ba : 0.0) << ",\n";
    oss << "  \"spread\": " << get_spread() << ",\n";
    oss << "  \"mid_price\": " << get_mid_price() << ",\n";
    
    // Bids
    oss << "  \"bids\": [\n";
    for (size_t i = 0; i < snapshot.bid_levels; i++) {
        oss << "    {\"price\": " << snapshot.bids[i].price 
            << ", \"qty\": " << snapshot.bids[i].total_quantity
            << ", \"orders\": " << snapshot.bids[i].order_count << "}";
        if (i < snapshot.bid_levels - 1) oss << ",";
        oss << "\n";
    }
    oss << "  ],\n";
    
    // Asks
    oss << "  \"asks\": [\n";
    for (size_t i = 0; i < snapshot.ask_levels; i++) {
        oss << "    {\"price\": " << snapshot.asks[i].price 
            << ", \"qty\": " << snapshot.asks[i].total_quantity
            << ", \"orders\": " << snapshot.asks[i].order_count << "}";
        if (i < snapshot.ask_levels - 1) oss << ",";
        oss << "\n";
    }
    oss << "  ],\n";
    
    // Statistics
    oss << "  \"stats\": {\n";
    oss << "    \"order_count\": " << get_order_count() << ",\n";
    oss << "    \"trade_count\": " << trade_count_ << ",\n";
    oss << "    \"traded_volume\": " << traded_volume_ << "\n";
    oss << "  }\n";
    
    oss << "}";
    
    return oss.str();
}

// ============================================================================
// STATISTICS
// ============================================================================

size_t OrderBook::get_order_count() const {
    return order_index_.size();
}

size_t OrderBook::get_bid_level_count() const {
    return bids_.size();
}

size_t OrderBook::get_ask_level_count() const {
    return asks_.size();
}

double OrderBook::get_total_bid_volume() const {
    double total = 0.0;
    for (const auto& [price, queue] : bids_) {
        for (const auto& order : queue) {
            total += order.remaining_qty();
        }
    }
    return total;
}

double OrderBook::get_total_ask_volume() const {
    double total = 0.0;
    for (const auto& [price, queue] : asks_) {
        for (const auto& order : queue) {
            total += order.remaining_qty();
        }
    }
    return total;
}

void OrderBook::set_trade_callback(TradeCallback callback) {
    trade_callback_ = std::move(callback);
}

void OrderBook::clear() {
    bids_.clear();
    asks_.clear();
    order_index_.clear();
    recent_trades_.clear();
    trade_count_ = 0;
    traded_volume_ = 0.0;
}

std::vector<Trade> OrderBook::get_recent_trades(size_t count) const {
    if (count >= recent_trades_.size()) {
        return recent_trades_;
    }
    
    return std::vector<Trade>(
        recent_trades_.end() - static_cast<ptrdiff_t>(count),
        recent_trades_.end()
    );
}

} // namespace institutional





