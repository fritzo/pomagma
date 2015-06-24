#include <atomic>
#include <deque>
#include <mutex>
#include <pomagma/util/util.hpp>

// TODO be less naive:
// #include <leveldb/db.h>
// #include <stxxl/queue>
// #include <tbb/concurrent_queue.h>

namespace pomagma {

class NaiveBroker : noncopyable
{
    struct Message
    {
        std::string data;
        uint32_t pending;

        // std::atomic<uint_least32_t> pending;
        // Message () : pending(0) {}
    };

public:

    typedef uint32_t topic_t;

    NaiveBroker (size_t topic_count)
        : m_queues(topic_count),
          m_subscriber_counts(topic_count, 0)
    {
    }

    NaiveBroker ()
    {
        for (const auto & queue : m_queues) {
            POMAGMA_ASSERT(queue.empty(), "lost messages");
        }
    }

    size_t topic_count () const { return m_queues.size(); }

    void subscribe (topic_t topic)
    {
        POMAGMA_ASSERT_LT(topic, topic_count());
        m_subscriber_counts[topic] += 1;
    }

    void write (topic_t topic, const std::string & data)
    {
        POMAGMA_ASSERT1(topic < topic_count(), "bad topic: " << topic);
        POMAGMA_ASSERT1(m_subscriber_counts[topic], "no subscribers");
        auto & queue = m_queues[topic];
        std::unique_lock<std::mutex> lock(m_mutex);
        queue.push_back({data, m_subscriber_counts[topic]});
    }

    bool try_read (topic_t topic, std::string & data)
    {
        POMAGMA_ASSERT1(topic < topic_count(), "bad topic: " << topic);
        POMAGMA_ASSERT1(m_subscriber_counts[topic], "no subscribers");
        auto & queue = m_queues[topic];
        std::unique_lock<std::mutex> lock(m_mutex);
        if (unlikely(queue.empty())) {
            return false;
        } else {
            Message & message = queue.front();
            data = message.data;
            if (--message.pending == 0) {
                queue.pop_front();
            }
            return true;
        }
    }

private:

    std::vector<std::deque<Message>> m_queues;
    std::vector<uint32_t> m_subscriber_counts;
    std::mutex m_mutex;
};

} // namespace pomagma
