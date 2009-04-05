require 'rubygems'
require 'hpricot'
require 'faster_csv'
require 'optparse'
require 'fileutils'
require 'open-uri'
require 'time'
require 'mechanize'

# Include this module in your scraper and implement a scrape_bills method that
# takes a chamber and a year and a state method that returns the state abbr.  
# at the bottom of your file call the run method.  
#  
# Your script doesn't need to worry about creating and managing csv files or state 
# directories.  This script handles all of that.
#
# Example
#
#  module MyState
#    include Scrapable
#
#   def self.state
#     "ms"
#   end
#
#   def self.scrap_bills(chamber, year)
#      bills = your_fetch_bills_method
#      bills.each do |bill|
#       add_bill(bill.to_hash)
#      end
#    end
#  end
#
#  MyState.run
#
module Scrapable
  include FileUtils
  class NoDataForYearError < ::StandardError 
    def initialize(year, msg)
      super "Unable to parse #{year}: #{msg}"
    end
  end
  
  def self.included(base)
    base.extend(self)
  end
  
  def options
    @options ||= {
      :years => [], 
      :chambers => []
    }
  end
  
  # Add a bill to the legislation.csv file
  def add_bill(bill_hash)
    @legislation_csv << bill_hash
  end
  
  # Add a bill version to the bill_versions.csv file
  def add_bill_version(version_hash)
    @bill_versions_csv << version_hash
  end
  
  # Add a sponsorship to the sponsorship.csv file
  def add_sponsorship(sponsorship_hash)
    @sponsorships_csv << sponsorship_hash
  end
  
  # Add an action to the actions.csv file
  def add_action(action_hash)
    @actions_csv << action_hash
  end
  
  # Run your parser, calling its scrape_bills method automatically passing in 
  # the chamber and years provided in the command line args.
  def run
    opts = OptionParser.new do |o|
      o.on("-y", "--years [YEARS]", "Years to parse") {|opt| options[:years] = opt}
      o.on(nil,  "--all", "Parse from 1969...2009") {|opt| options[:years] << 1969...2009}              
      o.on(nil,  "--upper", "Parse upper chamber") {|opt| options[:chambers] << 'upper'}  
      o.on(nil,  "--lower", "Parse lower chamber") {|opt| options[:chambers] << 'lower'}              
    end.parse!
    
    setup_data_directories
    years = options[:years]
    options[:years] = years.kind_of?(String) ? years.strip.split(/\s+|,/i).compact.reject {|y| y.empty?} : years
    options[:chambers].each do |chamber|
      options[:years].each do |year|
        begin
          scrape_bills(chamber, year)
        rescue StandardError => e
          raise NoDataForYearError.new(year, e)
        end
      end
    end
  end
  
  private
  def setup_data_directories
    state_dir = File.join(File.dirname(__FILE__), '..', '..', 'data', state)
    mkdir(state_dir) unless File.exists?(state_dir)
    common_headers = [:bill_state, :bill_chamber, :bill_session, :bill_id]
    headers = {
      :legislation    => common_headers + [:bill_name],
      :bill_versions  => common_headers + [:version_name, :version_url],
      :actions        => common_headers + [:action_chamber, :action_text, :action_date],
      :sponsorships   => common_headers + [:sponsor_type, :sponsor_name]
    }
    
    %w(legislation actions bill_versions sponsorships).each do |type|
      csv = FasterCSV.open(File.join(state_dir, "#{type}.csv"), 'w', { 
        :headers => headers[type.to_sym],
        :skip_blanks => true
      })
      self.instance_variable_set("@#{type}_csv", csv)
    end
  end
end