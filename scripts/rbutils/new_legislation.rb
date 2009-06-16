require 'rubygems'
require 'json'
require 'optparse'
require 'fileutils'

class NoDataForYearError < ::StandardError
  def initialize(year, msg)
    super "Unable to parse #{year}: #{msg}"
  end
end

class LegislationScraper
  include FileUtils

  @@state = nil

  def scrape_legislators(chamber, year)
    raise NotImplementedError.new()
  end

  def scrape_bills(chamber, year)
    raise NotImplementedError.new()
  end

  def scrape_metadata
    {}
  end

  def add_bill(bill)
    name = File.join(@bills_dir, "#{bill[:session]}:#{bill[:chamber]}:#{bill[:bill_id]}.json")
    File.open(name, 'w') { |f| f.write(bill.to_json) }
  end

  def add_legislator(legislator)
    name = File.join(@legs_dir, "#{legislator[:session]}:#{legislator[:chamber]}:#{legislator[:district]}.json")
    File.open(name, 'w') { |f| f.write(legislator.to_json) }
  end

  def options
    @options ||= {
      :years => [],
      :chambers => []
    }
  end

  def run
    opts = OptionParser.new do |o|
      o.on("-y", "--years [YEARS]", "Years to parse") {|opt| options[:years] = opt}
      o.on(nil,  "--all", "Parse from 1969...2009") {|opt| options[:years] << 1969...2009}
      o.on(nil,  "--upper", "Parse upper chamber") {|opt| options[:chambers] << 'upper'}
      o.on(nil,  "--lower", "Parse lower chamber") {|opt| options[:chambers] << 'lower'}
    end.parse!

    if options[:chambers].length == 0
      options[:chambers] = ['upper', 'lower']
    end

    setup_data_directories
    add_metadata(scrape_metadata)

    years = options[:years]
    options[:years] = years.kind_of?(String) ? years.strip.split(/\s+|,/i).compact.reject {|y| y.empty?} : years
    options[:chambers].each do |chamber|
      options[:years].each do |year|
        begin
          scrape_legislators(chamber, year)
          scrape_bills(chamber, year)
        rescue StandardError => e
          raise NoDataForYearError.new(year, e)
        end
      end
    end
  end

  private
  def setup_data_directories
    @state_dir = File.join(File.dirname(__FILE__), '..', '..', 'data', @@state)
    @bills_dir = File.join(@state_dir, 'bills')
    @legs_dir = File.join(@state_dir, 'legislators')
    mkdir(@state_dir) unless File.exists?(@state_dir)
    mkdir(@bills_dir) unless File.exists?(@bills_dir)
    mkdir(@legs_dir) unless File.exists?(@legs_dir)
  end

  private
  def add_metadata(metadata)
    name = File.join(@state_dir, "state_metadata.json")
    File.open(name, 'w') { |f| f.write(metadata.to_json) }
  end
end

class Bill < Hash
  def initialize(session, chamber, bill_id, title, extra={})
    self[:session] = session
    self[:chamber] = chamber
    self[:bill_id] = bill_id
    self[:title] = title
    self[:sponsors] = []
    self[:versions] = []
    self[:actions] = []
    self[:votes] = []
    self.merge!(extra)
  end

  def add_sponsor(type, name, extra={})
    self[:sponsors].push({:type => type, :name => name}.merge(extra))
  end

  def add_version(name, url, extra={})
    self[:versions].push({:name => name, :url => url}.merge(extra))
  end

  def add_action(actor, action, date, extra={})
    self[:actions].push({:actor => actor, :action => action,
                          :date => date}.merge(extra))
  end

  def add_vote(vote)
    self[:votes].push(vote)
  end
end

class Vote < Hash
  def initialize(chamber, date, motion, passed, yes_count, no_count,
                 other_count, extra={})
    self[:chamber] = chamber
    self[:date] = date
    self[:motion] = motion
    self[:passed] = passed
    self[:yes_count] = yes_count
    self[:no_count] = no_count
    self[:other_count] = other_count
    self[:yes_votes] = []
    self[:no_votes] = []
    self[:other_votes] = []
    self.merge!(extra)
  end

  def yes(legislator)
    self[:yes_votes].push(legislator)
  end

  def no(legislator)
    self[:no_votes].push(legislator)
  end

  def other(legislator)
    self[:other_votes].push(legislator)
  end
end

class Legislator < Hash
  def initialize(session, chamber, district, full_name, first_name,
                 last_name, middle_name, party, extra={})
    self[:session] = session
    self[:chamber] = chamber
    self[:district] = district
    self[:full_name] = full_name
    self[:first_name] = first_name
    self[:last_name] = last_name
    self[:middle_name] = middle_name
    self[:party] = party
    self.merge!(extra)
  end
end
